from typing import Optional
"""
checks/nas/ups_status.py - UPS connection status check
检测 UPS 连接状态和电量
"""

import subprocess
import re
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class UPSStatusCheck(Check):
    """Check UPS (Uninterruptible Power Supply) status"""

    check_id = "ups_status"
    title = "UPS 连接状态"
    description = "检测 UPS 连接状态、电量和预计运行时间"
    category = CheckCategory.NAS

    # 电量警告阈值
    BATTERY_WARNING = 20  # 百分比
    BATTERY_CRITICAL = 10  # 百分比

    def run(self) -> CheckResult:
        """Run UPS status check"""
        ups_info = self._get_ups_status()

        if ups_info is None:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="未检测到 UPS（无 UPS 连接为正常）",
                current="无 UPS",
                expected="UPS 连接正常或无 UPS",
            )

        # 解析 UPS 数据
        status = ups_info.get("status", "unknown")
        battery = ups_info.get("battery_percent", 100)
        runtime = ups_info.get("runtime_minutes", 0)
        model = ups_info.get("model", "Unknown UPS")
        on_line = ups_info.get("on_line", False)

        # 在线状态
        if not on_line:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"UPS ({model}) 已断电！正在使用电池供电！",
                current=f"电池 {battery}%，预计 {runtime} 分钟",
                expected="UPS 正常接入电源",
                fix_available=True,
                fix_description="市电中断！UPS 正在供电，请尽快保存数据并正常关机",
            )

        # 电量过低
        if battery <= self.BATTERY_CRITICAL:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message=f"UPS ({model}) 电量仅剩 {battery}%（严重）",
                current=f"电池 {battery}%，预计 {runtime} 分钟",
                expected=f"电池 > {self.BATTERY_WARNING}%",
                fix_available=True,
                fix_description="UPS 电量严重不足，请立即保存数据并关机",
            )

        if battery <= self.BATTERY_WARNING:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"UPS ({model}) 电量 {battery}%，建议注意",
                current=f"电池 {battery}%，预计 {runtime} 分钟",
                expected=f"电池 > {self.BATTERY_WARNING}%",
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"UPS ({model}) 状态正常，电量 {battery}%，预计运行 {runtime} 分钟",
            current=f"电池 {battery}%，预计 {runtime} 分钟",
            expected="UPS 正常",
            details=ups_info,
        )

    def _get_ups_status(self) -> Optional[dict]:
        """Get UPS status from NUT (Network UPS Tools)"""
        ups_info = {}

        # 方法1: upsc（NUT 标准工具）
        try:
            result = subprocess.run(
                ["upsc", "ups@localhost"],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.splitlines():
                    if ":" in line:
                        key, val = line.split(":", 1)
                        key = key.strip()
                        val = val.strip()
                        ups_info[key] = val

                if ups_info:
                    return self._parse_nut_output(ups_info)
        except Exception:
            pass

        # 方法2: apcaccess（APC UPS 专用）
        try:
            result = subprocess.run(
                ["apcaccess"],
                capture_output=True, text=True, errors="replace", timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.splitlines():
                    if ":" in line:
                        key, val = line.split(":", 1)
                        ups_info[key.strip()] = val.strip()
                if ups_info:
                    return self._parse_apc_output(ups_info)
        except Exception:
            pass

        return None

    def _parse_nut_output(self, data: dict) -> dict:
        """Parse NUT upsc output"""
        return {
            "model": data.get("ups.model", "Unknown"),
            "status": data.get("ups.status", "unknown"),
            "battery_percent": int(float(data.get("battery.charge", 100))),
            "runtime_minutes": int(float(data.get("battery.runtime", 0))) // 60,
            "on_line": "OL" in data.get("ups.status", ""),
            "source": "NUT",
        }

    def _parse_apc_output(self, data: dict) -> dict:
        """Parse apcaccess output"""
        def parse_num(val: str) -> int:
            try:
                return int(float(val.split()[0]))
            except Exception:
                return 0

        status = data.get("STATUS", "unknown")
        return {
            "model": data.get("MODEL", "Unknown"),
            "status": status,
            "battery_percent": parse_num(data.get("BCHARGE", "100")),
            "runtime_minutes": parse_num(data.get("TIMELEFT", "0")),
            "on_line": "ONLINE" in status or "ON" in status,
            "source": "apcupsd",
        }
