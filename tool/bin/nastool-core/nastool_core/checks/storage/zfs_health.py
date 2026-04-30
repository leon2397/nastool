# -*- coding: utf-8 -*-
"""ZFS 存储池健康检测"""
from __future__ import annotations

import subprocess
from nastool_core.checks.decorators import check


@check(id="zfs_pool", category="STORAGE", title="ZFS Pool Health",
       description="检测 ZFS 存储池状态（仅 ZFS 系统）")
def zfs_health(ctx):
    try:
        r = subprocess.run(["zpool", "status"],
                          capture_output=True, text=True, errors="replace", timeout=15)
        if r.returncode != 0:
            return ctx.passed(current="not ZFS",
                            expected="ZFS healthy",
                            message="Not using ZFS storage",
                            severity="INFO")
        issues = [kw for kw in ["DEGRADED", "FAULTED", "UNAVAIL"]
                  if kw in r.stdout]
        if issues:
            return ctx.failed(current="error",
                            expected="healthy",
                            message="ZFS issues: " + "; ".join(issues),
                            severity="CRITICAL",
                            fix_available=True, fix_id="fix_zfs",
                            fix_command="zpool status",
                            fix_description="Check ZFS pool status",
                            fix_risk="high")
        return ctx.passed(current="healthy",
                        expected="healthy",
                        message="ZFS pool healthy")
    except FileNotFoundError:
        return ctx.passed(current="not ZFS",
                        expected="ZFS healthy",
                        message="Not using ZFS",
                        severity="INFO")
    except Exception as e:
        return ctx.passed(current="unknown",
                        expected="ZFS healthy",
                        message=f"Could not check ZFS: {e}",
                        severity="INFO")
