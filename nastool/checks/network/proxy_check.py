# -*- coding: utf-8 -*-
"""代理配置检测"""
import os
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class ProxyCheck(Check):
    check_id = "proxy_config"
    title = "代理配置"
    description = "检测系统代理环境变量配置"
    category = CheckCategory.NETWORK

    def run(self) -> CheckResult:
        env_vars = ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]
        configured = []
        for var in env_vars:
            val = os.environ.get(var, "")
            if val:
                configured.append(f"{var}={val[:50]}")
        if configured:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.INFO,
                message=f"代理已配置: {configured[0]}",
                current="configured", expected="none or configured",
            )
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.PASSED,
            message="未配置代理",
            current="none", expected="none",
        )
