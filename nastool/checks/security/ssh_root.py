# -*- coding: utf-8 -*-
"""SSH root login check"""
from __future__ import annotations

from checks.decorators import check


@check(id="ssh_root", category="SECURITY", title="SSH Root Login",
       description="检查 SSH root 登录是否已禁用")
def ssh_root(ctx):
    sshd = "/etc/ssh/sshd_config"
    try:
        with open(sshd) as f:
            content = f.read()
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("PermitRootLogin"):
                val = line.split()[-1].lower()
                if val in ("no", "prohibit-password"):
                    return ctx.result(passed=True,
                                    current=val,
                                    expected="no or prohibit-password",
                                    message=f"Root login is {val}")
                if val == "yes":
                    return ctx.result(passed=False,
                                    current="yes",
                                    expected="no or prohibit-password",
                                    message="Root login is enabled (security risk)",
                                    severity="WARNING",
                                    fix_available=True, fix_id="disable_root_ssh",
                                    fix_command="sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config",
                                    fix_description="Disable SSH root login",
                                    fix_risk="low")
        return ctx.result(passed=False,
                        current="not set (default yes)",
                        expected="no or prohibit-password",
                        message="PermitRootLogin not set (default: yes)",
                        severity="WARNING",
                        fix_available=True, fix_id="set_permit_root",
                        fix_command="echo 'PermitRootLogin no' >> /etc/ssh/sshd_config",
                        fix_description="Set PermitRootLogin no",
                        fix_risk="low")
    except FileNotFoundError:
        return ctx.result(passed=True, current="n/a",
                        expected="n/a",
                        message="sshd_config not found (not an SSH server)",
                        severity="INFO")
    except Exception as e:
        return ctx.result(passed=True, current="unknown",
                        expected="no or prohibit-password",
                        message=f"Could not check SSH config: {e}",
                        severity="INFO")
