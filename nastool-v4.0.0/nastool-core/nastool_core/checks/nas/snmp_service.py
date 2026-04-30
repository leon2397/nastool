# -*- coding: utf-8 -*-
"""SNMP 服务检测"""
from __future__ import annotations
import subprocess
from nastool_core.checks.decorators import check

@check(id="snmp_service", category="NAS", title="SNMP Service",
       description="检测 SNMP 服务状态（监控数据采集）")
def snmp_service(ctx):
    try:
        r = subprocess.run(["pgrep", "-f", "snmpd"], capture_output=True, timeout=5)
        if r.returncode == 0:
            return ctx.passed(current="running", expected="running",
                            message="SNMP service running")
    except Exception:
        pass
    return ctx.passed(current="not running", expected="running",
                    message="SNMP not running", severity="INFO",
                    fix_available=True, fix_id="start_snmp",
                    fix_command="systemctl start snmpd",
                    fix_description="Start SNMP service",
                    fix_risk="low")
