# -*- coding: utf-8 -*-
"""默认路由检测"""
from __future__ import annotations

import subprocess
from nastool_core.checks.decorators import check


@check(id="default_route", category="NETWORK", title="Default Route",
       description="检测默认网关是否配置正确")
def route_check(ctx):
    try:
        r = subprocess.run(["ip", "route", "show"],
                          capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and ("default" in r.stdout.lower()
                                    or "0.0.0.0" in r.stdout):
            return ctx.passed(current="configured",
                            expected="configured",
                            message="Default route configured")
    except Exception:
        pass
    return ctx.failed(current="missing",
                    expected="configured",
                    message="No default route configured",
                    severity="CRITICAL",
                    fix_available=True, fix_id="configure_route",
                    fix_command="ip route add default via <gateway_ip>",
                    fix_description="Configure default gateway",
                    fix_risk="high")
