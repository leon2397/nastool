# -*- coding: utf-8 -*-
"""SNMP 服务检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class SNMPServiceCheck(Check):
    check_id = "snmp_service"
    title = "SNMP 服务"
    description = "检测 SNMP 服务状态（监控数据采集）"
    category = CheckCategory.NAS

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(["pgrep", "-f", "snmpd"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message="SNMP 服务运行中",
                    current="running", expected="running",
                )
        except Exception:
            pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=False,
            severity=CheckSeverity.INFO,
            message="SNMP 服务未运行",
            current="not running", expected="running",
            fix_available=True, fix_id="start_snmp",
            fix_command="systemctl start snmpd",
            fix_description="启动 SNMP 服务",
            fix_risk="low",
        )
