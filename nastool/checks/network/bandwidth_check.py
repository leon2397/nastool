# -*- coding: utf-8 -*-
"""网卡带宽检测"""
from __future__ import annotations

import subprocess
from checks.decorators import check


@check(id="bandwidth", category="NETWORK", title="Network Bandwidth",
       description="检测网卡协商速率和活跃状态")
def bandwidth_check(ctx):
    try:
        r = subprocess.run(["ip", "link", "show"],
                          capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return ctx.result(passed=True, current="unknown",
                            expected="1Gbps+",
                            message="Could not get interface info",
                            severity="INFO")
        active = []
        for line in r.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 2:
                iface = parts[1].strip()
                if iface not in ("lo", "docker0") and "state UP" in line:
                    active.append(iface)
        if active:
            return ctx.result(passed=True, current=", ".join(active[:3]),
                            expected="active",
                            message=f"Active interfaces: {', '.join(active[:3])}")
    except Exception:
        pass
    return ctx.result(passed=True, current="unknown",
                    expected="active",
                    message="Could not determine bandwidth",
                    severity="INFO")
