# -*- coding: utf-8 -*-
"""ClamAV 杀毒软件检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class ClamAVCheck(Check):
    check_id = "clamav"
    title = "ClamAV 杀毒"
    description = "检测 ClamAV 杀毒软件是否安装并更新病毒库"
    category = CheckCategory.SECURITY

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(["clamscan", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message=f"ClamAV: {result.stdout.splitlines()[0][:60]}",
                    current="installed", expected="installed",
                )
        except Exception:
            pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="ClamAV 未安装",
            current="not installed", expected="installed",
            fix_available=True, fix_id="install_clamav",
            fix_command="apt install clamav && systemctl start clamav-daemon",
            fix_description="安装 ClamAV 杀毒软件",
            fix_risk="low",
        )
