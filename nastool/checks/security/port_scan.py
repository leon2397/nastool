# -*- coding: utf-8 -*-
"""异常端口检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class PortScanCheck(Check):
    check_id = "suspicious_ports"
    title = "异常端口"
    description = "检测监听端口，排除可疑端口"
    category = CheckCategory.SECURITY

    SUSPICIOUS = ["31337", "12345", "54321", "1337", "4444", "5555"]

    def run(self) -> CheckResult:
        suspicious_found = []
        try:
            result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                result = subprocess.run(["netstat", "-tlnp"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for port in self.SUSPICIOUS:
                    if f":{port}" in result.stdout:
                        suspicious_found.append(port)
        except Exception:
            pass

        if suspicious_found:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.WARNING,
                message=f"发现可疑端口: {', '.join(suspicious_found)}",
                current="suspicious", expected="clean",
                fix_available=True, fix_id="investigate_ports",
                fix_description="调查并关闭可疑端口",
                fix_risk="high",
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.PASSED,
            message="未发现可疑监听端口",
            current="clean", expected="clean",
        )
