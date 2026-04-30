# -*- coding: utf-8 -*-
"""网络延迟检测"""

import subprocess

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class NetworkLatencyCheck(Check):
    """检测网络延迟"""

    check_id = "network_latency"
    title = "网络延迟"
    description = "测量到主要节点的延迟，检测网络质量"
    category = CheckCategory.NETWORK

    def __init__(self):
        super().__init__()
        # 检测目标：DNS / CDN / 国内主要节点
        self.targets = [
            ("223.5.5.5", "阿里DNS"),
            ("119.29.29.29", "腾讯DNS"),
            ("8.8.8.8", "Google DNS"),
            ("114.114.114.114", "114DNS"),
        ]

    def run(self) -> CheckResult:
        latency_results = []
        issues = []

        for target, name in self.targets:
            try:
                result = subprocess.run(
                    ["ping", "-n", "3", "-w", "500", target]
                    if subprocess.os.name == "nt"
                    else ["ping", "-c", "3", "-W", "1", target],
                    capture_output=True, text=True, errors="replace", timeout=10
                )
                if result.returncode == 0:
                    output = result.stdout
                    # 解析平均延迟
                    if "Minimum" in output:
                        import re
                        match = re.search(r"Minimum = (\d+)ms", output)
                        if not match:
                            match = re.search(r"Minimum = (\d+)ms", output)
                        if not match:
                            match = re.search(r"min/avg/max.*?=\s*(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)", output)
                            if match:
                                avg = float(match.group(2))
                            else:
                                avg = None
                        else:
                            avg = float(match.group(1))
                    else:
                        # Windows 格式
                        import re
                        match = re.search(r"Minimum = (\d+)ms", output)
                        if match:
                            avg = float(match.group(1))
                        else:
                            avg = None

                    if avg is not None:
                        latency_results.append((name, target, avg))
                        if avg > 200:
                            issues.append(f"{name}({target}) 延迟 {avg}ms 偏高")
            except Exception:
                pass

        if not latency_results:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=True,
                severity=CheckSeverity.INFO,
                message="无法测量网络延迟",
                current="unknown",
                expected="<200ms",
            ))

        avg_all = sum(r[2] for r in latency_results) / len(latency_results)
        best = min(latency_results, key=lambda x: x[2])

        if issues:
            return self._enhance_result_with_accuracy(CheckResult(
                check_id=self.check_id, title=self.title,
                category=self.category, passed=False,
                severity=CheckSeverity.WARNING,
                message=f"平均延迟 {avg_all:.0f}ms，最佳: {best[0]} {best[2]:.0f}ms",
                current=f"{avg_all:.0f}ms",
                expected="<200ms",
                details={"results": latency_results},
            ))

        return CheckResult(
            check_id=self.check_id, title=self.title,
            category=self.category, passed=True,
            severity=CheckSeverity.PASSED,
            message=f"网络延迟正常，平均 {avg_all:.0f}ms，最佳: {best[0]} {best[2]:.0f}ms",
            current=f"{avg_all:.0f}ms",
            expected="<200ms",
            details={"results": latency_results},
        )
