# -*- coding: utf-8 -*-
"""网络延迟检测"""
from __future__ import annotations

import re
import subprocess
from checks.decorators import check


@check(id="latency_check", category="NETWORK", title="Latency Check",
       description="测量到主要节点的延迟，检测网络质量")
def latency_check(ctx):
    targets = [
        ("223.5.5.5", "AliDNS"),
        ("119.29.29.29", "TencentDNS"),
        ("8.8.8.8", "GoogleDNS"),
        ("114.114.114.114", "114DNS"),
    ]
    results, issues = [], []

    for target, name in targets:
        try:
            import os as _os
            if _os.name == "nt":
                cmd = ["ping", "-n", "3", "-w", "500", target]
            else:
                cmd = ["ping", "-c", "3", "-W", "1", target]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode != 0:
                continue
            output = r.stdout
            avg = None
            m = re.search(r"min/avg/max[^=]*=\s*(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)", output)
            if m:
                avg = float(m.group(2))
            if avg is None:
                m = re.search(r"Average[=\s]*(\d+)ms", output, re.IGNORECASE)
                if m:
                    avg = float(m.group(1))
            if avg is not None:
                results.append((name, target, avg))
                if avg > 200:
                    issues.append(f"{name} {avg:.0f}ms high")
        except Exception:
            pass

    if not results:
        return ctx.passed(current="unknown",
                         expected="<200ms",
                         message="Could not measure latency",
                         severity="INFO")

    avg_all = sum(r[2] for r in results) / len(results)
    best = min(results, key=lambda x: x[2])

    if issues:
        return ctx.failed(current=f"{avg_all:.0f}ms",
                         expected="<200ms",
                         message=f"Avg {avg_all:.0f}ms, best {best[0]} {best[2]:.0f}ms",
                         severity="WARNING",
                         details={"results": [(n, t, str(v)) for n, t, v in results]})

    return ctx.passed(current=f"{avg_all:.0f}ms",
                     expected="<200ms",
                     message=f"Latency OK: avg {avg_all:.0f}ms, best {best[0]} {best[2]:.0f}ms",
                     details={"results": [(n, t, str(v)) for n, t, v in results]})
