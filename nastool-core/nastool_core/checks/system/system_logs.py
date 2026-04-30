# -*- coding: utf-8 -*-
"""系统日志检测"""
from __future__ import annotations

import os
from nastool_core.checks.decorators import check


@check(id="system_logs", category="SYSTEM", title="System Logs",
       description="检查系统日志目录是否有异常大文件", enable_accuracy=True)
def system_logs(ctx):
    log_dirs = ["/var/log", "/run/log"]
    found_dir = None
    for d in log_dirs:
        if os.path.isdir(d):
            found_dir = d
            break

    if not found_dir:
        return ctx.passed(current="unknown",
                          expected="detectable",
                          message="No standard log directory found",
                          severity="INFO")

    large_files = []
    total_mb = 0
    try:
        for entry in os.scandir(found_dir):
            if entry.is_file():
                size_mb = entry.stat().st_size / (1024**2)
                total_mb += size_mb
                if size_mb > 100:
                    large_files.append(f"{entry.name} ({size_mb:.0f}MB)")
    except PermissionError:
        return ctx.passed(current="no access",
                          expected="readable",
                          message="No permission to read log directory",
                          severity="INFO")

    if large_files:
        return ctx.passed(current=f"{total_mb:.0f}MB total",
                          expected="< 1GB",
                          message=f"Large log files: {', '.join(large_files[:3])}",
                          severity="WARNING",
                          fix_available=True,
                          fix_id="cleanup_logs",
                          fix_command=f"journalctl --vacuum-time=7d && rm -rf {found_dir}/*.gz",
                          fix_description="Clean up old log files",
                          fix_risk="low",
                          details={"large_files": large_files, "total_mb": round(total_mb)})

    return ctx.passed(current=f"{total_mb:.0f}MB",
                      expected="< 1GB",
                      message=f"Log directory size normal: {total_mb:.0f}MB",
                      details={"total_mb": round(total_mb)})
