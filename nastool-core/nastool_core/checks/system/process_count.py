# -*- coding: utf-8 -*-
"""进程数检测"""
from __future__ import annotations

import subprocess
from nastool_core.checks.decorators import check


@check(id="process_count", category="SYSTEM", title="Process Count",
       description="检查系统进程数是否异常", enable_accuracy=True)
def process_count(ctx):
    try:
        if __import__("os").name == "nt":
            r = subprocess.run('powershell "Get-Process | Measure-Object | Select-Object -ExpandProperty Count"',
                               shell=True, capture_output=True, text=True, errors="replace", timeout=10)
            count = int(r.stdout.strip())
        else:
            r = subprocess.run("ps aux | wc -l", shell=True,
                               capture_output=True, text=True, errors="replace", timeout=5)
            count = int(r.stdout.strip()) - 1  # subtract header
    except Exception:
        return ctx.passed(current="unknown",
                          expected="detectable",
                          message="Could not determine process count",
                          severity="INFO")

    max_normal = 500
    warn = 300
    if count > max_normal:
        return ctx.failed(current=str(count),
                          expected=f"< {max_normal}",
                          message=f"Too many processes ({count}), possible fork bomb",
                          severity="WARNING")
    elif count > warn:
        return ctx.passed(current=str(count),
                          expected=f"< {max_normal}",
                          message=f"High process count ({count}), monitoring",
                          severity="WARNING")
    return ctx.passed(current=str(count),
                      expected=f"< {max_normal}",
                      message=f"{count} processes running")
