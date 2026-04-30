# -*- coding: utf-8 -*-
"""端口冲突检测"""
from __future__ import annotations

import socket
import subprocess
from nastool_core.checks.decorators import check


@check(id="port_conflict", category="NETWORK", title="Port Conflict",
       description="检查 NAS 常用端口是否被占用")
def port_conflict(ctx):
    check_ports = [9999, 8000]
    conflicts, available = [], []

    for port in check_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            r = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if r == 0:
                # Port in use
                info = ""
                for cmd in ["netstat -tlnp", "ss -tlnp"]:
                    try:
                        pr = subprocess.run(cmd, shell=True,
                                          capture_output=True, text=True, timeout=5)
                        for line in (pr.stdout + pr.stderr).splitlines():
                            if str(port) in line:
                                info = line.strip()
                                break
                    except Exception:
                        pass
                conflicts.append({"port": port, "info": info})
            else:
                available.append(port)
        except Exception:
            available.append(port)

    if not conflicts:
        return ctx.passed(current=f"{len(available)} available",
                         expected="all available",
                         message=f"All ports free: {available}")
    ports = [c["port"] for c in conflicts]
    return ctx.passed(current=f"{len(available)} free, {len(conflicts)} used",
                      expected="all available",
                      message=f"Ports in use: {ports}",
                      severity="WARNING",
                      details={"conflicts": conflicts, "available": available})
