# -*- coding: utf-8 -*-
"""SFTP 服务检测"""
from __future__ import annotations
import subprocess
from checks.decorators import check

@check(id="sftp_service", category="NAS", title="SFTP Service",
       description="检测 SFTP (SSH File Transfer) 服务状态")
def sftp_service(ctx):
    try:
        r = subprocess.run(["pgrep", "-f", "sshd"], capture_output=True, timeout=5)
        if r.returncode == 0:
            return ctx.result(passed=True, current="running", expected="running",
                            message="SSH/SFTP service running")
    except Exception:
        pass
    return ctx.result(passed=True, current="not running", expected="running",
                    message="SFTP not running", severity="INFO")
