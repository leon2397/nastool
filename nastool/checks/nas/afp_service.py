# -*- coding: utf-8 -*-
"""AFP 服务检测"""
from __future__ import annotations
import subprocess
from checks.decorators import check

@check(id="afp_service", category="NAS", title="AFP Service",
       description="检测 AFP (Apple Filing Protocol) 服务状态")
def afp_service(ctx):
    try:
        r = subprocess.run(["pgrep", "-f", "afpd"], capture_output=True, timeout=5)
        if r.returncode == 0:
            return ctx.passed(current="running", expected="running",
                            message="AFP service running")
    except Exception:
        pass
    return ctx.passed(current="not running", expected="running",
                    message="AFP not running (Mac users only)",
                    severity="INFO")
