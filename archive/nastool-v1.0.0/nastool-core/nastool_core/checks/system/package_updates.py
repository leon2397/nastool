# -*- coding: utf-8 -*-
"""包更新检测"""
from __future__ import annotations

import shutil
import subprocess
from nastool_core.checks.decorators import check


@check(id="package_updates", category="SYSTEM", title="Package Updates",
       description="检测待安装的系统包更新数量")
def package_updates(ctx):
    for pkg_mgr in ["apt-get", "yum", "dnf", "pacman"]:
        if not shutil.which(pkg_mgr):
            continue
        try:
            if pkg_mgr == "apt-get":
                r = subprocess.run(["apt-get", "-s", "upgrade"],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    count = r.stdout.count("\n")
                    if count >= 50:
                        return ctx.result(
                            passed=False, current=f"{count} updates",
                            expected="up to date",
                            message=f"{count} packages pending update",
                            severity="CRITICAL",
                            fix_available=True, fix_id="update_system",
                            fix_command="apt update && apt upgrade -y",
                            fix_description="Run system update",
                            fix_risk="medium")
                    elif count >= 10:
                        return ctx.result(
                            passed=False, current=f"{count} updates",
                            expected="up to date",
                            message=f"{count} packages pending update",
                            severity="WARNING",
                            fix_available=True, fix_id="update_system",
                            fix_command="apt update && apt upgrade -y",
                            fix_description="Run system update",
                            fix_risk="medium")
                    return ctx.result(
                        passed=True, current="up to date",
                        expected="up to date",
                        message="System packages up to date")
        except Exception:
            pass
    return ctx.result(
        passed=True, current="unknown", expected="detectable",
        message="Could not check updates (permission denied or non-Linux)",
        severity="INFO")
