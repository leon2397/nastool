# -*- coding: utf-8 -*-
"""SELinux configuration check"""
from __future__ import annotations

import subprocess
from nastool_core.checks.decorators import check


@check(id="selinux", category="SECURITY", title="SELinux Configuration",
       description="检查 SELinux 是否允许 NAS 操作")
def selinux(ctx):
    try:
        r = subprocess.run(["getenforce"],
                          capture_output=True, text=True, errors="replace", timeout=5)
        status = r.stdout.strip().lower()
        if status == "disabled":
            return ctx.passed(current="Disabled",
                            expected="Permissive or Disabled",
                            message="SELinux is disabled")
        if status == "permissive":
            return ctx.passed(current="Permissive",
                            expected="Permissive for NAS",
                            message="SELinux is permissive (logging only)")
        if status == "enforcing":
            return ctx.failed(current="Enforcing",
                            expected="Permissive for NAS",
                            message="SELinux enforcing - may block NAS operations",
                            severity="WARNING",
                            fix_available=True, fix_id="set_permissive",
                            fix_command="setenforce 0",
                            fix_description="Set SELinux to permissive",
                            fix_risk="medium")
        return ctx.passed(current=status,
                        expected="Permissive or Disabled",
                        message=f"SELinux status: {status}")
    except FileNotFoundError:
        return ctx.passed(current="not installed",
                        expected="Not required",
                        message="SELinux not installed")
    except Exception as e:
        return ctx.passed(current="unknown",
                        expected="Permissive or Disabled",
                        message=f"Could not check SELinux: {e}",
                        severity="INFO")
