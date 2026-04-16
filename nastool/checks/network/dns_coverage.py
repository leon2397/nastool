# -*- coding: utf-8 -*-
"""DNS 覆盖检测"""
from __future__ import annotations

import re
import subprocess
from checks.decorators import check

MIN_NS = 2
RECOMMENDED_NS = 3
RECOMMENDED_DNS = {"8.8.8.8", "8.8.4.4", "223.5.5.5", "223.6.6.6", "1.1.1.1", "1.0.0.1"}


def _parse_resolv():
    try:
        with open("/etc/resolv.conf") as f:
            return re.findall(r"^nameserver\s+(\S+)", f.read(), re.MULTILINE)
    except Exception:
        return None


def _ping_ns(ns):
    try:
        r = subprocess.run(["ping", "-c", "1", "-W", "2", ns],
                          capture_output=True, text=True, timeout=3)
        m = re.search(r"time[=<]?(\d+\.?\d*)\s*ms", r.stdout, re.IGNORECASE)
        return float(m.group(1)) if m else -1
    except Exception:
        return -1


@check(id="dns_coverage", category="NETWORK", title="DNS Coverage",
       description="检查 /etc/resolv.conf DNS 服务器数量和覆盖质量")
def dns_coverage(ctx):
    nameservers = _parse_resolv()

    if nameservers is None:
        return ctx.failed(current="unreadable",
                         expected=f">= {MIN_NS} nameservers",
                         message="Could not read /etc/resolv.conf",
                         severity="CRITICAL",
                         fix_available=True, fix_id="setup_dns",
                         fix_command="echo 'nameserver 223.5.5.5' >> /etc/resolv.conf",
                         fix_description="Configure DNS servers",
                         fix_risk="medium")

    count = len(nameservers)
    used_rec = [ns for ns in nameservers if ns in RECOMMENDED_DNS]

    if count == 0:
        return ctx.failed(current="0 nameservers",
                         expected=f">= {MIN_NS}",
                         message="No DNS servers configured",
                         severity="CRITICAL",
                         fix_available=True, fix_id="setup_dns",
                         fix_command="echo 'nameserver 223.5.5.5' >> /etc/resolv.conf",
                         fix_description="Configure DNS",
                         fix_risk="medium")

    speeds = [(ns, _ping_ns(ns)) for ns in nameservers[:3]]
    details = {"nameservers": nameservers, "speeds": [(n, str(s)) for n, s in speeds]}

    if count == 1:
        return ctx.failed(current="1 nameserver",
                         expected=f">= {MIN_NS}",
                         message=f"Only 1 DNS server ({nameservers[0]}) - single point of failure",
                         severity="WARNING",
                         fix_available=True, fix_id="add_dns",
                         fix_command="echo 'nameserver 223.5.5.5' >> /etc/resolv.conf",
                         fix_description="Add backup DNS server",
                         fix_risk="low",
                         details=details)

    if count >= RECOMMENDED_NS:
        msg = f"DNS OK ({count} servers), {len(used_rec)} recommended"
    else:
        msg = f"DNS basic ({count} servers), recommend {RECOMMENDED_NS}+"

    sev = "PASSED" if count >= RECOMMENDED_NS else "WARNING"
    return ctx.result(passed=count >= MIN_NS,
                     current=f"{count}: {', '.join(nameservers[:3])}",
                     expected=f">= {RECOMMENDED_NS}",
                     message=msg, severity=sev,
                     details=details)
