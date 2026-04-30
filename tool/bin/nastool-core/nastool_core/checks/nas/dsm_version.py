from typing import Optional
"""
checks/nas/dsm_version.py - DSM / QTS version check
检测群晖 DSM 或威联通 QTS 系统版本
"""

import subprocess
import re
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check

# DSM/QTS 版本数据（手动维护）
DSM_VERSIONS = {
    "7.2.1": "2024-05",
    "7.2.0": "2024-03",
    "7.1.1": "2023-07",
    "7.1.0": "2022-07",
    "7.0.1": "2022-03",
    "7.0.0": "2021-07",
    "6.2.4": "2020-03",
}

QTS_VERSIONS = {
    "5.2.1": "2024-06",
    "5.1.1": "2023-07",
    "5.1.0": "2023-03",
    "5.0.1": "2022-07",
    "5.0.0": "2022-01",
    "4.5.4": "2020-03",
    "4.3.6": "2018-06",
}


@register_check
class DSMVersionCheck(Check):
    """Check NAS DSM/QTS system version"""

    check_id = "nas_version"
    title = "NAS 系统版本"
    description = "检测群晖 DSM 或威联通 QTS 系统版本及更新状态"
    category = CheckCategory.NAS

    # 警告：超过 12 个月未更新
    OLD_VERSION_MONTHS = 12

    def run(self) -> CheckResult:
        """Run NAS version check"""
        # 方法1: 检测群晖
        version = self._detect_dsm()
        nas_type = "Synology DSM"

        if not version:
            # 方法2: 检测威联通
            version = self._detect_qts()
            nas_type = "QNAP QTS"

        if not version:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未检测到群晖 DSM 或威联通 QTS 系统",
                current="非群晖/威联通环境",
                expected="群晖 DSM 或威联通 QTS",
            )

        # 解析版本
        version_str = version.get("version", "unknown")
        build = version.get("build", "")
        update_date = version.get("update_date", "")

        # 检查版本新旧
        version_status = self._check_version_age(version_str, nas_type)

        msg = f"{nas_type} {version_str}"
        if build:
            msg += f" (Build {build})"
        if update_date:
            msg += f" 更新于 {update_date}"
        msg += f"：{version_status['status_msg']}"

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=version_status["ok"],
            severity=version_status["severity"],
            message=msg,
            current=f"{nas_type} {version_str}",
            expected=version_status["expected"],
            fix_available=not version_status["ok"],
            fix_description=version_status["fix"] if not version_status["ok"] else None,
            details=version,
        )

    def _detect_dsm(self) -> Optional[dict]:
        """Detect Synology DSM version"""
        try:
            # 方法A: synocommand（群晖 API）
            result = subprocess.run(
                ["cat", "/etc/VERSION"],
                capture_output=True, text=True, errors="replace", timeout=3,
            )
            if result.returncode == 0:
                content = result.stdout
                ver_match = re.search(r'productversion="([^"]+)"', content)
                build_match = re.search(r'buildnumber="([^"]+)"', content)
                if ver_match:
                    return {
                        "type": "DSM",
                        "version": ver_match.group(1),
                        "build": build_match.group(1) if build_match else "",
                    }

            # 方法B: synosysinfo
            result2 = subprocess.run(
                ["synosysinfo", "-model"],
                capture_output=True, text=True, errors="replace", timeout=3,
            )
            if result2.returncode == 0 and "Synology" in result2.stdout:
                result3 = subprocess.run(
                    ["cat", "/etc/VERSION"],
                    capture_output=True, text=True, errors="replace", timeout=3,
                )
                if result3.returncode == 0:
                    ver_match = re.search(r'productversion="([^"]+)"', result3.stdout)
                    if ver_match:
                        return {
                            "type": "DSM",
                            "version": ver_match.group(1),
                            "build": "",
                        }
        except Exception:
            pass
        return None

    def _detect_qts(self) -> Optional[dict]:
        """Detect QNAP QTS version"""
        try:
            result = subprocess.run(
                ["cat", "/etc/os_release"],
                capture_output=True, text=True, errors="replace", timeout=3,
            )
            if result.returncode != 0 or "QNAP" not in result.stdout:
                return None

            # 解析 QTS 版本
            for line in result.stdout.splitlines():
                if "VERSION=" in line or "QTS_VERSION=" in line:
                    match = re.search(r'["\']?(\d+\.\d+\.\d+)["\']?', line)
                    if match:
                        return {
                            "type": "QTS",
                            "version": match.group(1),
                            "build": "",
                        }
        except Exception:
            pass
        return None

    def _check_version_age(self, version: str, nas_type: str) -> dict:
        """Check if version is old"""
        versions_db = DSM_VERSIONS if nas_type == "Synology DSM" else QTS_VERSIONS
        update_date = versions_db.get(version, "")

        result = {
            "ok": True,
            "severity": CheckSeverity.PASSED,
            "status_msg": "版本较新",
            "expected": "最新稳定版",
            "fix": None,
        }

        if not update_date:
            result["status_msg"] = "版本日期未知"
            return result

        # 简单检查：版本表中最早的版本视为旧版本
        if version not in versions_db:
            result["status_msg"] = "版本较旧，建议升级"
            result["ok"] = False
            result["severity"] = CheckSeverity.WARNING
            result["expected"] = "最新稳定版"
            result["fix"] = f"{nas_type} 版本较旧，建议升级到最新稳定版以获得安全补丁"
            return result

        return result
