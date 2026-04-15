# -*- coding: utf-8 -*-
"""DNS 缓存服务检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class DNSCacheCheck(Check):
    check_id = "dns_cache"
    title = "DNS 缓存"
    description = "检测 DNS 缓存服务（dnsmasq/systemd-resolved）"
    category = CheckCategory.NETWORK

    def run(self) -> CheckResult:
        for svc in ["dnsmasq", "systemd-resolved", "nscd", "unbound", "bind9"]:
            try:
                result = subprocess.run(["pgrep", "-f", svc], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return CheckResult(
                        check_id=self.check_id, title=self.title,
                        category=self.category, passed=True,
                        severity=CheckSeverity.PASSED,
                        message=f"DNS 缓存服务: {svc}",
                        current="running", expected="running",
                    )
            except Exception:
                pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="未检测到 DNS 缓存服务",
            current="not running", expected="running",
            fix_available=True, fix_id="setup_dnscache",
            fix_description="安装 dnsmasq",
            fix_risk="low",
        )
