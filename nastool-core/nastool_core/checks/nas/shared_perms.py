from typing import Optional
"""
checks/nas/shared_perms.py - Shared folder permission check
检测 NAS 共享文件夹权限配置
"""

import subprocess
import re
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class SharedPermsCheck(Check):
    """Check NAS shared folder permissions"""

    check_id = "shared_perms"
    title = "共享文件夹权限"
    description = "检测 NAS 共享文件夹权限配置，识别权限过大的配置"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        """Run shared folder permissions check"""
        folders = self._get_shared_folders()

        if folders is None:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="非群晖/威联通环境，无法获取共享文件夹列表",
                current="无数据",
                expected="权限配置正确",
            ))

        if not folders:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未找到共享文件夹（正常）",
                current="0 个共享文件夹",
                expected="少量共享文件夹",
            ))

        # 检测权限过大的文件夹
        issues = []
        for folder in folders:
            if folder.get("public", False) and folder.get("rw_all", False):
                issues.append(f"{folder['name']} 完全公开读写")
            elif folder.get("public", False) and not folder.get("has_auth", True):
                issues.append(f"{folder['name']} 无需认证即可访问")

        if issues:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"发现 {len(issues)} 个权限过大的共享文件夹",
                current=", ".join(issues[:3]),
                expected="共享文件夹权限适当",
                details={"folders": folders, "issues": issues},
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"{len(folders)} 个共享文件夹权限配置正常",
            current=f"{len(folders)} 个文件夹",
            expected="权限配置合理",
            details={"folders": folders},
        )

    def _get_shared_folders(self) -> Optional[list]:
        """Get list of shared folders with permissions"""
        folders = []

        # 群晖：/etc/samba/smb.conf
        try:
            result = subprocess.run(
                ["cat", "/etc/samba/smb.conf"],
                capture_output=True, text=True, errors="replace", timeout=3,
            )
            if result.returncode == 0:
                current = {}
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("[") and line.endswith("]"):
                        if current:
                            folders.append(current)
                        current = {"name": line[1:-1]}
                    elif "=" in line:
                        key, val = line.split("=", 1)
                        current[key.strip()] = val.strip()
                if current:
                    folders.append(current)
                if folders:
                    return folders
        except Exception:
            pass

        # 威联通：/etc/config/smb.conf
        try:
            result = subprocess.run(
                ["find", "/etc", "-name", "smb*.conf", "-maxdepth", "3"],
                capture_output=True, text=True, errors="replace", timeout=3,
            )
            if result.returncode == 0:
                for conf_file in result.stdout.strip().splitlines()[:2]:
                    result2 = subprocess.run(
                        ["cat", conf_file],
                        capture_output=True, text=True, errors="replace", timeout=3,
                    )
                    if result2.returncode == 0:
                        # 解析 shares
                        current = {}
                        for line in result2.stdout.splitlines():
                            line = line.strip()
                            if line.startswith("[") and line.endswith("]"):
                                if current:
                                    folders.append(current)
                                current = {"name": line[1:-1]}
                        if current:
                            folders.append(current)
                        if folders:
                            return folders
        except Exception:
            pass

        # 通用 Linux：/etc/samba/smb.conf
        try:
            result = subprocess.run(
                ["cat", "/etc/samba/smb.conf"],
                capture_output=True, text=True, errors="replace", timeout=3,
            )
            if result.returncode == 0 and result.stdout.strip():
                current = {}
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("[") and line.endswith("]") and "homes" not in line:
                        if current:
                            folders.append(current)
                        current = {"name": line[1:-1]}
                if current:
                    folders.append(current)
                if folders:
                    return folders
        except Exception:
            pass

        return None
