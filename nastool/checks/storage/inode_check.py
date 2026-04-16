# -*- coding: utf-8 -*-
"""Inode 使用率检测"""
from __future__ import annotations

import subprocess
from checks.decorators import check


@check(id="inode_usage", category="STORAGE", title="Inode Usage",
       description="检测文件系统 inode 使用率（文件数量限制）")
def inode_check(ctx):
    issues, ok_parts = [], []
    try:
        r = subprocess.run(["df", "-i"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            for line in r.stdout.strip().splitlines()[1:]:
                parts = [p.strip() for p in line.split()]
                if len(parts) >= 6:
                    try:
                        pct = int(parts[4].replace("%", ""))
                        mnt = parts[5]
                        if pct >= 95:
                            issues.append(f"{mnt}: {pct}% CRITICAL")
                        elif pct >= 80:
                            issues.append(f"{mnt}: {pct}%")
                        else:
                            ok_parts.append(f"{mnt}: {pct}%")
                    except ValueError:
                        pass
    except Exception:
        pass
    if issues:
        return ctx.failed(current="high inode",
                        expected="<80%",
                        message="; ".join(issues[:3]),
                        severity="CRITICAL" if any("CRITICAL" in i for i in issues) else "WARNING",
                        fix_available=True, fix_id="clean_inodes",
                        fix_command="find / -type f -atime +30 -delete",
                        fix_description="Clean up small files or increase inode count",
                        fix_risk="medium")
    if ok_parts:
        return ctx.passed(current="normal",
                        expected="<80%",
                        message=f"Inode OK: {ok_parts[0]}")
    return ctx.passed(current="unknown",
                    expected="<80%",
                    message="Could not get inode info",
                    severity="INFO")
