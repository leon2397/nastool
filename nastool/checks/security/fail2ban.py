# -*- coding: utf-8 -*-
"""Fail2ban 防暴力破解检测"""
from __future__ import annotations

import subprocess
from checks.decorators import check


@check(id="fail2ban", category="SECURITY", title="Fail2ban Service",
       description="检测 Fail2ban 防暴力破解服务是否运行")
def fail2ban(ctx):
    try:
        r = subprocess.run(["pgrep", "-f", "fail2ban"],
                          capture_output=True, timeout=5)
        if r.returncode == 0:
            return ctx.passed(current="running",
                            expected="running",
                            message="Fail2ban is running")
    except Exception:
        pass
    return ctx.passed(current="not running",
                    expected="running",
                    message="Fail2ban not running",
                    severity="INFO",
                    fix_available=True, fix_id="install_fail2ban",
                    fix_command="apt install fail2ban",
                    fix_description="Install Fail2ban",
                    fix_risk="low")
