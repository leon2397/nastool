# -*- coding: utf-8 -*-
"""SSH 安全配置检测"""
from __future__ import annotations

import os
from nastool_core.checks.decorators import check


@check(id="ssh_config", category="SECURITY", title="SSH Security Config",
       description="检测 SSH 配置安全性（密码登录/密钥/端口）", enable_accuracy=True)
def ssh_config(ctx):
    warnings = []
    for cfg in ["/etc/ssh/sshd_config", "/etc/ssh/sshd_config"]:
        if not os.path.exists(cfg):
            continue
        try:
            lines = [l.strip() for l in open(cfg).readlines()
                    if l.strip() and not l.strip().startswith("#")]
            cd = {}
            for line in lines:
                parts = line.split(None, 1)
                if len(parts) >= 2:
                    cd[parts[0].lower()] = parts[1].lower()
            if cd.get("passwordauthentication", "yes") == "yes":
                warnings.append("Password auth enabled (use key-based)")
            if cd.get("permitrootlogin", "prohibit-password") not in ("no", "without-password"):
                warnings.append("Root login allowed")
            if cd.get("port", "22") == "22":
                warnings.append("Using default port 22")
            break
        except Exception:
            pass
    if warnings:
        return ctx.failed(current="insecure",
                        expected="secure",
                        message="; ".join(warnings),
                        severity="WARNING",
                        fix_available=True, fix_id="harden_ssh",
                        fix_command="sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config",
                        fix_description="Disable password auth, use SSH keys",
                        fix_risk="medium")
    return ctx.passed(current="secure",
                    expected="secure",
                    message="SSH configuration is secure")
