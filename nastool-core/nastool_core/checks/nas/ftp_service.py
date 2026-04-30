# -*- coding: utf-8 -*-
"""FTP 服务检测"""
from __future__ import annotations
import subprocess
from nastool_core.checks.decorators import check

@check(id="ftp_service", category="NAS", title="FTP Service",
       description="检测 FTP 服务状态（vsftpd/proftpd/pure-ftpd）", enable_accuracy=True)
def ftp_service(ctx):
    for proc in ["vsftpd", "proftpd", "pure-ftpd"]:
        try:
            r = subprocess.run(["pgrep", "-f", proc], capture_output=True, timeout=5)
            if r.returncode == 0:
                return ctx.passed(current="running", expected="running",
                                message=f"{proc} running")
        except Exception:
            pass
    return ctx.passed(current="not running", expected="running",
                    message="FTP not running",
                    severity="INFO")
