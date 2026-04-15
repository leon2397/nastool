# -*- coding: utf-8 -*-
"""AFP 服务检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class AFPServiceCheck(Check):
    check_id = "afp_service"
    title = "AFP 服务"
    description = "检测 AFP (Apple Filing Protocol) 服务状态"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(["pgrep", "-f", "afpd"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message="AFP 服务运行中",
                    current="running", expected="running",
                )
        except Exception:
            pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="AFP 服务未运行（Mac 用户可忽略）",
            current="not running", expected="running",
        )
