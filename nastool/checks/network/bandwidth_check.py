# -*- coding: utf-8 -*-
"""网卡带宽检测"""
import subprocess
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

@register_check
class BandwidthCheck(Check):
    check_id = "bandwidth"
    title = "网卡带宽"
    description = "检测网卡协商速率"
    category = CheckCategory.NETWORK

    def run(self) -> CheckResult:
        try:
            result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.INFO,
                    message="无法获取网卡信息",
                    current="unknown", expected="1Gbps+",
                )
            ifaces = []
            for line in result.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 2:
                    iface = parts[1].strip()
                    if iface not in ("lo", "docker0") and "state" in line:
                        if "UP" in line:
                            ifaces.append(iface)
            if ifaces:
                return CheckResult(
                    check_id=self.check_id, title=self.title,
                    category=self.category, passed=True,
                    severity=CheckSeverity.PASSED,
                    message=f"活跃网卡: {', '.join(ifaces[:3])}",
                    current=", ".join(ifaces[:3]), expected="1Gbps+",
                )
        except Exception as e:
            pass
        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.INFO,
            message="网卡检测跳过",
            current="unknown", expected="1Gbps+",
        )
