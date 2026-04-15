# -*- coding: utf-8 -*-
"""Fail2ban 防暴力破解检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class Fail2banCheck(Check):
    check_id = "fail2ban"
    title = "Fail2ban"
    description = "检测 Fail2ban 防暴力破解服务是否运行"
    category = CheckCategory.SECURITY

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(["pgrep", "-f", "fail2ban"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message="Fail2ban 运行中",
                    current="running", expected="running",
                )
        except Exception:
            pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="Fail2ban 未运行",
            current="not running", expected="running",
            fix_available=True, fix_id="install_fail2ban",
            fix_command="apt install fail2ban",
            fix_description="安装 Fail2ban 防暴力破解",
            fix_risk="low",
        )
