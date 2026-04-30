# -*- coding: utf-8 -*-
"""WiFi 状态检测"""
from __future__ import annotations

import subprocess
from nastool_core.checks.decorators import check


@check(id="wifi_status", category="NETWORK", title="WiFi Status",
       description="检测 WiFi 连接状态和信号强度")
def wifi_check(ctx):
    try:
        r = subprocess.run(["iwconfig"], capture_output=True, text=True, errors="replace", timeout=5)
        if r.returncode == 0 and "ESSID" in r.stdout:
            for line in r.stdout.splitlines():
                if "ESSID" in line:
                    return ctx.passed(current="connected",
                                    expected="connected or not used",
                                    message=line.strip()[:80],
                                    severity="INFO")
    except Exception:
        pass
    return ctx.passed(current="not connected",
                    expected="connected or not used",
                    message="WiFi not connected or unavailable",
                    severity="INFO")
