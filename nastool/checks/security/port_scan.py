# -*- coding: utf-8 -*-
"""异常端口检测"""
from __future__ import annotations

import subprocess
from checks.decorators import check

SUSPICIOUS = ["31337", "12345", "54321", "1337", "4444", "5555"]


@check(id="suspicious_ports", category="SECURITY", title="Suspicious Ports",
       description="检测监听端口，排除可疑端口")
def port_scan(ctx):
    found = []
    for cmd in ["ss -tlnp", "netstat -tlnp"]:
        try:
            r = subprocess.run(cmd, shell=True,
                             capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                for port in SUSPICIOUS:
                    if f":{port}" in r.stdout:
                        found.append(port)
                if found:
                    break
        except Exception:
            pass
    if found:
        return ctx.result(passed=False, current="suspicious",
                        expected="clean",
                        message=f"Suspicious ports found: {', '.join(found)}",
                        severity="WARNING",
                        fix_available=True, fix_id="investigate_ports",
                        fix_command=f"ss -tlnp | grep {found[0]}",
                        fix_description="Investigate and close suspicious ports",
                        fix_risk="high")
    return ctx.result(passed=True, current="clean",
                    expected="clean",
                    message="No suspicious listening ports detected")
