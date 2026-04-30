# -*- coding: utf-8 -*-
"""定时任务检测"""
from __future__ import annotations

import os
import subprocess
from nastool_core.checks.decorators import check


@check(id="cron_jobs", category="SYSTEM", title="Cron Jobs",
       description="检测定时任务配置，识别过多任务")
def cron_jobs(ctx):
    total = 0
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, errors="replace", timeout=5)
        if r.returncode == 0:
            total += len([l for l in r.stdout.splitlines()
                         if l.strip() and not l.strip().startswith("#")])
    except Exception:
        pass
    for path in ["/etc/crontab", "/etc/cron.d/", "/etc/cron.hourly/"]:
        if os.path.isdir(path):
            try:
                total += len([f for f in os.listdir(path) if not f.startswith(".")])
            except Exception:
                pass
        elif os.path.exists(path):
            total += 1

    if total > 30:
        return ctx.failed(current=f"{total} jobs",
                          expected="< 30",
                          message=f"Too many cron jobs ({total})",
                          severity="WARNING")
    return ctx.passed(current=f"{total} jobs",
                      expected="< 30",
                      message=f"{total} cron jobs configured")
