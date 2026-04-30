# -*- coding: utf-8 -*-
"""Internet connectivity check"""
from __future__ import annotations

import socket
from nastool_core.checks.decorators import check

TEST_HOSTS = [
    ("baidu.com", 80),
    ("google.com", 80),
    ("github.com", 443),
]


def _can_reach(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        # 先尝试DNS解析
        ip = socket.gethostbyname(host)
        # 然后尝试连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


@check(id="internet_access", category="NETWORK", title="Internet Access",
       description="检查设备是否能访问互联网", enable_accuracy=True)
def internet_access(ctx):
    reachable, unreachable = [], []
    for host, port in TEST_HOSTS:
        if _can_reach(host, port):
            reachable.append(host)
        else:
            unreachable.append(host)

    # 要求至少2个主机可访问才算连接成功
    if len(reachable) >= 2:
        return ctx.passed(current="connected",
                         expected="connected",
                         message=f"Internet reachable via: {', '.join(reachable)}",
                         details={"reachable": reachable, "unreachable": unreachable})
    # 如果只有1个主机可访问，返回警告
    elif len(reachable) == 1:
        return ctx.failed(current="limited",
                        expected="connected",
                        message=f"Limited internet access: only {reachable[0]} reachable",
                        severity="WARNING",
                        details={"reachable": reachable, "unreachable": unreachable})
    # 如果没有主机可访问，返回错误
    return ctx.failed(current="disconnected",
                    expected="connected",
                    message="No internet access detected",
                    severity="CRITICAL",
                    fix_available=True, fix_id="fix_network",
                    fix_command="Check gateway, DNS, and firewall settings",
                    fix_description="Check network configuration",
                    fix_risk="medium",
                    details={"unreachable": unreachable})
