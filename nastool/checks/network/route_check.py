# -*- coding: utf-8 -*-
"""默认路由检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class RouteCheck(Check):
    check_id = "default_route"
    title = "默认路由"
    description = "检测默认网关是否配置正确"
    category = CheckCategory.NETWORK

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(["ip", "route", "show"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and ("default" in result.stdout.lower() or "0.0.0.0" in result.stdout):
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message="默认路由已配置",
                    current="configured", expected="configured",
                )
        except Exception:
            pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.CRITICAL,
            message="默认网关未配置",
            current="missing", expected="configured",
            fix_available=True, fix_id="configure_route",
            fix_description="配置默认网关",
            fix_risk="high",
        )
