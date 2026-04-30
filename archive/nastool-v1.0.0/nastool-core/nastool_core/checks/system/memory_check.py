# -*- coding: utf-8 -*-
"""系统内存检测"""
from __future__ import annotations

import subprocess
from nastool_core.checks.decorators import check


@check(id="memory_check", category="SYSTEM", title="System Memory",
       description="检查系统内存是否充足")
def memory_check(ctx):
    try:
        r = subprocess.run(
            "powershell -Command \"(Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize\"",
            shell=True, capture_output=True, text=True, timeout=10
        )
        # TotalVisibleMemorySize 单位是 KB，需要转换为 GB
        total_kb = float(r.stdout.strip())
        total = total_kb / 1024 / 1024  # 转换为 GB
    except Exception:
        try:
            r = subprocess.run("free -m", shell=True,
                               capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace")
            lines = r.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                total = float(parts[1]) / 1024  # 转换为 GB
            else:
                total = 0
        except Exception:
            total = 0

    if total == 0:
        return ctx.passed(current="unknown",
                          expected="detectable",
                          message="Could not determine memory",
                          severity="INFO")

    min_required = 1.0   # GB
    if total < min_required:
        return ctx.failed(current=f"{total:.1f}GB",
                          expected=f">= {min_required:.0f}GB",
                          message=f"Memory {total:.1f}GB below minimum {min_required:.0f}GB",
                          severity="WARNING")
    return ctx.passed(current=f"{total:.1f}GB",
                      expected=f">= {min_required:.0f}GB",
                      message=f"Memory {total:.1f}GB available")
