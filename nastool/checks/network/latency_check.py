# -*- coding: utf-8 -*-
"""网络延迟检测"""

import subprocess
import re

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class NetworkLatencyCheck(Check):
    """检测网络延迟"""

    check_id = "network_latency"
    title = "网络延迟"
    description = "测量到主要 DNS 节点的延迟，检测网络质量"
    category = CheckCategory.NETWORK

    def run(self) -> CheckResult:
        targets = [
            ("223.5.5.5", "阿里DNS"),
            ("119.29.29.29", "腾讯DNS"),
            ("8.8.8.8", "Google DNS"),
            ("114.114.114.114", "114DNS"),
        ]

        latency_results = []
        issues = []

        for target, name in targets:
            try:
                if subprocess.os.name == "nt":
                    cmd = ["ping", "-n", "3", "-w", "500", target]
                else:
                    cmd = ["ping", "-c", "3", "-W", "1", target]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    output = result.stdout
                    # 解析延迟
                    avg = None
                    if "Minimum" in output or "minimum" in output.lower():
                        # Linux
                        m = re.search(r"min/avg/max[^=]*=\s*(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)", output)
                        if m:
                            avg = float(m.group(2))
                    if avg is None and "Average" in output:
                        # Windows
                        m = re.search(r"Average[=\s]*(\d+)ms", output, re.IGNORECASE)
                        if m:
                            avg = float(m.group(1))
                    if avg is not None:
                        latency_results.append((name, target, avg))
                        if avg > 200:
                            issues.append(f"{name} {avg:.0f}ms 偏高")
            except Exception:
                pass

        if not latency_results:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.INFO,
                message="无法测量网络延迟",
                current="unknown", expected="<200ms",
            )

        avg_all = sum(r[2] for r in latency_results) / len(latency_results)
        best = min(latency_results, key=lambda x: x[2])

        if issues:
            return CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.WARNING,
                message=f"平均 {avg_all:.0f}ms，最佳 {best[0]} {best[2]:.0f}ms；{issues[0]}",
                current=f"{avg_all:.0f}ms", expected="<200ms",
                fix_available=True, fix_id="check_network",
                fix_description="检查网络连接质量",
                fix_risk="low",
                details={"results": latency_results},
            )

        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.PASSED,
            message=f"延迟正常，平均 {avg_all:.0f}ms，最佳 {best[0]} {best[2]:.0f}ms",
            current=f"{avg_all:.0f}ms", expected="<200ms",
            details={"results": latency_results},
        )
