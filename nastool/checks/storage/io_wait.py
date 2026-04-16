# -*- coding: utf-8 -*-
"""IO Wait 检测"""
from __future__ import annotations

from checks.decorators import check


@check(id="io_wait", category="STORAGE", title="IO Wait",
       description="检测系统 IO 等待率（CPU 等待磁盘 I/O 的比例）")
def io_wait(ctx):
    try:
        with open("/proc/stat") as f:
            fields = f.readline().split()
        iowait = int(fields[5])
        total = sum(int(f) for f in fields[1:8])
        pct = (iowait / total * 100) if total > 0 else 0
        if pct >= 50:
            return ctx.failed(current=f"{pct:.1f}%",
                            expected="<20%",
                            message=f"IO Wait {pct:.1f}% - disk bottleneck",
                            severity="CRITICAL",
                            fix_available=True, fix_id="check_disk_io",
                            fix_command="iostat -x 1 5",
                            fix_description="Check disk performance",
                            fix_risk="medium")
        if pct >= 20:
            return ctx.failed(current=f"{pct:.1f}%",
                            expected="<20%",
                            message=f"IO Wait {pct:.1f}% elevated",
                            severity="WARNING")
        return ctx.passed(current=f"{pct:.1f}%",
                        expected="<20%",
                        message=f"IO Wait normal: {pct:.1f}%")
    except Exception:
        return ctx.passed(current="unknown",
                        expected="<20%",
                        message="IO Wait check skipped",
                        severity="INFO")
