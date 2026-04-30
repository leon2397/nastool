# -*- coding: utf-8 -*-
"""Firewall configuration check"""
from __future__ import annotations

import subprocess
from nastool_core.checks.decorators import check

NAS_PORTS = [8000, 443, 80]


@check(id="firewall", category="SECURITY", title="Firewall Configuration",
       description="检查防火墙是否允许 NAS 服务端口", enable_accuracy=True)
def firewall(ctx):
    try:
        r = subprocess.run(["ufw", "status"],
                          capture_output=True, text=True, errors="replace", timeout=5)
        if "inactive" in r.stdout:
            return ctx.passed(current="inactive",
                            expected="active with NAS ports allowed",
                            message="Firewall is inactive (all ports open)",
                            severity="WARNING",
                            fix_available=True, fix_id="enable_firewall",
                            fix_command="ufw allow 8000/tcp && ufw allow 443/tcp && ufw enable",
                            fix_description="Enable firewall and allow NAS ports",
                            fix_risk="medium")
        allowed = [p for p in NAS_PORTS if str(p) in r.stdout]
        missing = [p for p in NAS_PORTS if p not in allowed]
        if not missing:
            return ctx.passed(current=f"Ports {allowed} allowed",
                            expected="All NAS ports allowed",
                            message=f"All NAS ports allowed: {allowed}")
        return ctx.failed(current=f"Ports {allowed} allowed",
                        expected="All NAS ports allowed",
                        message=f"Missing: {missing}",
                        severity="WARNING",
                        fix_available=True, fix_id="allow_ports",
                        fix_command=f"ufw allow {missing[0]}/tcp",
                        fix_description=f"Allow port {missing[0]}",
                        fix_risk="low")
    except FileNotFoundError:
        return ctx.passed(current="not installed",
                        expected="Firewall recommended",
                        message="ufw not installed",
                        severity="INFO")
    except Exception as e:
        return ctx.passed(current="unknown",
                        expected="Firewall recommended",
                        message=f"Could not check firewall: {e}",
                        severity="INFO")
