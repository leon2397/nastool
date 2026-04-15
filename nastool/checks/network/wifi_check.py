# -*- coding: utf-8 -*-
"""WiFi 状态检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class WiFiCheck(Check):
    check_id = "wifi_status"
    title = "WiFi 状态"
    description = "检测 WiFi 连接状态和信号强度"
    category = CheckCategory.NETWORK

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(["iwconfig"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and "ESSID" in result.stdout:
                lines = result.stdout.splitlines()
                info = [l.strip()[:80] for l in lines if "ESSID" in l or "Signal" in l]
                if info:
                    return CheckResult(
                        check_id=self.check_id, title=self.title,
                        category=self.category, passed=True,
                        severity=CheckSeverity.INFO,
                        message=info[0][:80],
                        current="connected", expected="connected or not used",
                    )
        except Exception:
            pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.INFO,
            message="WiFi 未连接或不可用",
            current="not connected", expected="connected or not used",
        )
