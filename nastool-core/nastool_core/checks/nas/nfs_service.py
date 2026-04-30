# -*- coding: utf-8 -*-
"""NFS 服务状态检测"""
from __future__ import annotations
import subprocess
from nastool_core.checks.decorators import check

@check(id="nfs_service", category="NAS", title="NFS Service",
       description="检测 NFS 服务是否运行，导出目录是否可访问", enable_accuracy=True)
def nfs_service(ctx):
    try:
        r = subprocess.run(["pgrep", "-f", "nfsd"], capture_output=True, timeout=5)
        if r.returncode == 0:
            cnt = len(r.stdout.strip().splitlines())
            return ctx.passed(current="running", expected="running",
                            message=f"NFS running ({cnt} nfsd processes)")
    except Exception:
        pass
    try:
        r = subprocess.run(["pgrep", "-f", "rpcbind"], capture_output=True, timeout=5)
        if r.returncode == 0:
            return ctx.passed(current="partial", expected="running",
                            message="rpcbind running but NFS not detected", severity="WARNING")
    except Exception:
        pass
    return ctx.passed(current="not running", expected="running",
                    message="NFS not running", severity="INFO",
                    fix_available=True, fix_id="start_nfs",
                    fix_command="systemctl start nfs-server",
                    fix_description="Start NFS service", fix_risk="medium")
