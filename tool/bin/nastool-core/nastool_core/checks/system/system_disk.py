# -*- coding: utf-8 -*-
"""系统磁盘空间检测"""
from __future__ import annotations

import os
from nastool_core.checks.decorators import check


@check(id="system_disk", category="SYSTEM", title="System Disk Space",
       description="检查系统盘可用空间是否充足")
def system_disk(ctx):
    try:
        if os.name == "nt":
            import subprocess
            r = subprocess.run(
                'powershell -Command "(Get-PSDrive C).Free/1GB"',
                shell=True, capture_output=True, text=True, timeout=10
            )
            free_gb = float(r.stdout.strip())
        else:
            stat = os.statvfs("/")
            free_gb = stat.f_bavail * stat.f_frsize / (1024**3)
    except Exception:
        return ctx.passed(current="unknown",
                          expected="detectable",
                          message="Could not determine disk space",
                          severity="INFO")

    min_free = 10.0  # GB
    if free_gb < min_free:
        return ctx.failed(current=f"{free_gb:.1f}GB",
                          expected=f">= {min_free:.0f}GB free",
                          message=f"Only {free_gb:.1f}GB free, minimum {min_free:.0f}GB required",
                          severity="CRITICAL",
                          fix_available=True,
                          fix_id="cleanup_tmp_space",
                          fix_command="docker system prune -af && rm -rf /tmp/*",
                          fix_description="Clean up disk space",
                          fix_risk="medium")
    return ctx.passed(current=f"{free_gb:.1f}GB",
                      expected=f">= {min_free:.0f}GB free",
                      message=f"{free_gb:.1f}GB free on system disk")
