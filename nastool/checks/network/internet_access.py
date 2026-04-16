# -*- coding: utf-8 -*-
"""Internet connectivity check"""
from __future__ import annotations

import socket
from checks.decorators import check

TEST_HOSTS = [
    ("baidu.com", 80),
    ("google.com", 80),
    ("github.com", 443),
]


def _can_reach(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


@check(id="internet_access", category="NETWORK", title="Internet Access",
       description="检查设备是否能访问互联网")
def internet_access(ctx):
    reachable, unreachable = [], []
    for host, port in TEST_HOSTS:
        if _can_reach(host, port):
            reachable.append(host)
        else:
            unreachable.append(host)

    if reachable:
        return ctx.result(passed=True,
                         current="connected",
                         expected="connected",
                         message=f"Internet reachable via: {', '.join(reachable)}",
                         details={"reachable": reachable, "unreachable": unreachable})
    return ctx.result(passed=False,
                    current="disconnected",
                    expected="connected",
                    message="No internet access detected",
                    severity="CRITICAL",
                    fix_available=True, fix_id="fix_network",
                    fix_command="Check gateway, DNS, and firewall settings",
                    fix_description="Check network configuration",
                    fix_risk="medium",
                    details={"unreachable": unreachable})
