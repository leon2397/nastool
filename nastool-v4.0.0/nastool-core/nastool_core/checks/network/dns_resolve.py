# -*- coding: utf-8 -*-
"""DNS 解析检测"""
from __future__ import annotations

import socket
from nastool_core.checks.decorators import check


@check(id="dns_resolve", category="NETWORK", title="DNS Resolution",
       description="检查 DNS 解析是否正常")
def dns_resolve(ctx):
    domains = ["baidu.com", "google.com", "github.com"]
    resolved, failed = [], []
    dns_servers = []
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                if line.startswith("nameserver"):
                    dns_servers.append(line.split()[1])
    except Exception:
        pass
    for domain in domains:
        try:
            ip = socket.gethostbyname(domain)
            resolved.append({"domain": domain, "ip": ip})
        except socket.gaierror:
            failed.append(domain)

    if not failed:
        return ctx.passed(current="working",
                         expected="working",
                         message=f"DNS resolution working ({len(resolved)}/{len(domains)})",
                         details={"resolved": resolved, "dns_servers": dns_servers})
    return ctx.failed(current="failed",
                      expected="working",
                      message=f"DNS failed for: {', '.join(failed)}",
                      severity="CRITICAL",
                      fix_available=True, fix_id="fix_dns",
                      fix_command="echo 'nameserver 8.8.8.8' >> /etc/resolv.conf",
                      fix_description="Configure DNS (e.g. 8.8.8.8)",
                      fix_risk="low",
                      details={"failed": failed, "dns_servers": dns_servers})
