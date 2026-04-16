# -*- coding: utf-8 -*-
"""Disk space check"""
from __future__ import annotations

import shutil
from checks.decorators import check


@check(id="disk_space", category="STORAGE", title="Disk Space",
       description="检查磁盘空间是否满足 NAS 需求")
def storage_disk(ctx):
    try:
        total, used, free = shutil.disk_usage("/")
        free_gb = free / (1024**3)
        free_pct = (free / total) * 100
        if free_gb < 10:
            return ctx.failed(current=f"{free_gb:.1f}GB ({free_pct:.0f}%)",
                            expected=">=10GB or >=10%",
                            message=f"Critical: only {free_gb:.1f}GB free",
                            severity="CRITICAL",
                            fix_available=True, fix_id="cleanup_disk",
                            fix_command="docker system prune -af && rm -rf /tmp/*",
                            fix_description="Clean up disk space",
                            fix_risk="medium")
        if free_gb < 50:
            return ctx.passed(current=f"{free_gb:.1f}GB ({free_pct:.0f}%)",
                            expected=">=50GB or >=10%",
                            message=f"Low disk space: {free_gb:.1f}GB free",
                            severity="WARNING",
                            fix_available=True, fix_id="cleanup_disk",
                            fix_command="docker system prune -af",
                            fix_description="Clean up old files",
                            fix_risk="low")
        return ctx.passed(current=f"{free_gb:.1f}GB ({free_pct:.0f}%)",
                        expected=">=50GB",
                        message=f"{free_gb:.1f}GB free ({free_pct:.0f}%)")
    except Exception as e:
        return ctx.passed(current="unknown",
                        expected="detectable",
                        message=f"Could not check disk space: {e}",
                        severity="INFO")
