# -*- coding: utf-8 -*-
"""MTU 检测"""
from __future__ import annotations

import re
import subprocess
from checks.decorators import check


@check(id="mtu_size", category="NETWORK", title="MTU Size",
       description="检测网卡 MTU 设置是否合理")
def mtu_check(ctx):
    issues, ok_nics = [], []
    try:
        r = subprocess.run(["ip", "link", "show"],
                          capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                if "mtu" in line:
                    m = re.search(r"mtu\s+(\d+)", line)
                    if m:
                        mtu = int(m.group(1))
                        parts = line.split(":")
                        iface = parts[1].strip() if len(parts) > 1 else "?"
                        if mtu < 1400:
                            issues.append(f"{iface}: {mtu}")
                        else:
                            tag = " (Jumbo)" if mtu >= 9000 else ""
                            ok_nics.append(f"{iface}: {mtu}{tag}")
    except Exception:
        pass

    if issues:
        return ctx.result(passed=False, current="MTU too small",
                         expected="1400+",
                         message="; ".join(issues),
                         severity="WARNING",
                         fix_available=True, fix_id="set_mtu",
                         fix_command="ip link set eth0 mtu 1500",
                         fix_description="Adjust MTU to 1500",
                         fix_risk="medium")
    if ok_nics:
        return ctx.result(passed=True, current="normal",
                         expected="1400+",
                         message=", ".join(ok_nics[:3]))
    return ctx.result(passed=True, current="unknown",
                     expected="1400+",
                     message="Could not determine MTU",
                     severity="INFO")
