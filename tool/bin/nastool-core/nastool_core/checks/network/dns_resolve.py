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
    
    # 检查是否有DNS服务器配置
    if not dns_servers:
        return ctx.failed(current="no dns servers",
                          expected="working",
                          message="No DNS servers configured in /etc/resolv.conf",
                          severity="ERROR",
                          details={"dns_servers": []})
    
    # 测试DNS解析
    for domain in domains:
        try:
            # 设置超时，避免长时间阻塞
            import time
            start_time = time.time()
            ip = socket.gethostbyname(domain)
            resolve_time = time.time() - start_time
            if resolve_time > 5:
                failed.append(f"{domain} (timeout)")
            else:
                resolved.append({"domain": domain, "ip": ip})
        except socket.gaierror:
            failed.append(domain)
        except Exception:
            failed.append(f"{domain} (error)")

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
