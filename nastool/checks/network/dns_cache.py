# -*- coding: utf-8 -*-
"""DNS 缓存服务检测"""
from __future__ import annotations

import subprocess
from checks.decorators import check


@check(id="dns_cache", category="NETWORK", title="DNS Cache Service",
       description="检测 DNS 缓存服务（dnsmasq/systemd-resolved）")
def dns_cache(ctx):
    for svc in ["dnsmasq", "systemd-resolved", "nscd", "unbound", "bind9"]:
        try:
            r = subprocess.run(["pgrep", "-f", svc],
                              capture_output=True, timeout=5)
            if r.returncode == 0:
                return ctx.passed(current="running",
                                 expected="running",
                                 message=f"DNS cache service: {svc}",
                                 severity="PASSED")
        except Exception:
            pass
    return ctx.passed(current="not running",
                      expected="running",
                      message="No DNS cache service detected",
                      severity="INFO",
                      fix_available=True, fix_id="setup_dnscache",
                      fix_command="apt install dnsmasq",
                      fix_description="Install dnsmasq DNS cache",
                      fix_risk="low")
