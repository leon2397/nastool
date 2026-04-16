# -*- coding: utf-8 -*-
"""SELinux configuration check"""
from __future__ import annotations

import subprocess
from checks.decorators import check


@check(id="selinux", category="SECURITY", title="SELinux Configuration",
       description="检查 SELinux 是否允许 NAS 操作")
def selinux(ctx):
    try:
        r = subprocess.run(["getenforce"],
                          capture_output=True, text=True, timeout=5)
        status = r.stdout.strip().lower()
        if status == "disabled":
            return ctx.result(passed=True, current="Disabled",
                            expected="Permissive or Disabled",
                            message="SELinux is disabled")
        if status == "permissive":
            return ctx.result(passed=True, current="Permissive",
                            expected="Permissive for NAS",
                            message="SELinux is permissive (logging only)")
        if status == "enforcing":
            return ctx.result(passed=False, current="Enforcing",
                            expected="Permissive for NAS",
                            message="SELinux enforcing - may block NAS operations",
                            severity="WARNING",
                            fix_available=True, fix_id="set_permissive",
                            fix_command="setenforce 0",
                            fix_description="Set SELinux to permissive",
                            fix_risk="medium")
        return ctx.result(passed=True, current=status,
                        expected="Permissive or Disabled",
                        message=f"SELinux status: {status}")
    except FileNotFoundError:
        return ctx.result(passed=True, current="not installed",
                        expected="Not required",
                        message="SELinux not installed")
    except Exception as e:
        return ctx.result(passed=True, current="unknown",
                        expected="Permissive or Disabled",
                        message=f"Could not check SELinux: {e}",
                        severity="INFO")
