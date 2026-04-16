# -*- coding: utf-8 -*-
"""SMB/CIFS 服务检测"""
from __future__ import annotations
import subprocess
from checks.decorators import check

@check(id="smb_service", category="NAS", title="SMB Service",
       description="检测 Samba (smbd) 服务是否运行")
def smb_service(ctx):
    try:
        r = subprocess.run(["pgrep", "-f", "smbd"], capture_output=True, timeout=5)
        if r.returncode == 0:
            cnt = len(r.stdout.strip().splitlines())
            return ctx.passed(current="running", expected="running",
                            message=f"SMB running ({cnt} processes)")
    except Exception:
        pass
    try:
        r = subprocess.run(["sc", "query", "LanmanServer"],
                          capture_output=True, text=True, timeout=10)
        if "RUNNING" in r.stdout or "START_PENDING" in r.stdout:
            return ctx.passed(current="running", expected="running",
                            message="SMB running (Windows Server service)")
    except Exception:
        pass
    return ctx.passed(current="not running", expected="running",
                    message="SMB not running", severity="INFO")
