# -*- coding: utf-8 -*-
"""网络延迟检测

改进版本 (v4.1):
- 多endpoint检测：DNS、CDN、云服务
- 增强解析：支持Linux/Windows多格式
- 数据融合：综合多个endpoint结果
- 丢包率检测：增加网络质量评估
"""

import subprocess
import re
import socket
from typing import Dict, List, Tuple, Optional

from ..base import Check, CheckResult, CheckCategory, CheckSeverity, DataSourceInfo
from ..registry import register_check


@register_check
class NetworkLatencyCheck(Check):
    """检测网络延迟 with multi-endpoint support"""

    check_id = "network_latency"
    title = "网络延迟"
    description = "测量到主要节点的延迟，检测网络质量"
    category = CheckCategory.NETWORK

    def __init__(self):
        super().__init__()
        self.targets = [
            ("223.5.5.5", "阿里DNS", "dns", 1.0),
            ("119.29.29.29", "腾讯DNS", "dns", 1.0),
            ("8.8.8.8", "Google DNS", "dns", 0.9),
            ("114.114.114.114", "114DNS", "dns", 1.0),
            ("www.baidu.com", "百度", "cdn", 0.8),
            ("www.aliyun.com", "阿里云", "cdn", 0.8),
            ("www.tencent.com", "腾讯", "cdn", 0.8),
            ("www.google.com", "Google", "cdn", 0.5),
        ]

    def run(self) -> CheckResult:
        latency_results = []
        issues = []
        sources_info = []

        for target, name, endpoint_type, weight in self.targets:
            source_info = DataSourceInfo(
                name=name,
                source_type=f"ping_{endpoint_type}",
                available=False,
                priority=int(weight * 100),
                last_value=None
            )

            resolved_ip = target
            if not self._is_ip(target):
                resolved_ip = self._resolve_domain(target)
                if not resolved_ip:
                    sources_info.append(source_info)
                    continue

            result_data = self._ping_target(resolved_ip, target, name)

            if result_data:
                source_info.available = True
                source_info.last_value = result_data
                sources_info.append(source_info)

                latency_results.append(result_data)
                if result_data["avg"] > 200:
                    issues.append(f"{name}({target}) 延迟 {result_data['avg']:.0f}ms")
                if result_data.get("loss", 0) > 5:
                    issues.append(f"{name}({target}) 丢包 {result_data['loss']:.0f}%")
            else:
                sources_info.append(source_info)

        if not latency_results:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="无法测量网络延迟",
                current="unknown",
                expected="<200ms",
            )

        avg_all = sum(r["avg"] for r in latency_results) / len(latency_results)
        best = min(latency_results, key=lambda x: x["avg"])
        avg_loss = sum(r.get("loss", 0) for r in latency_results) / len(latency_results)

        if issues:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"平均延迟 {avg_all:.0f}ms，最佳: {best['name']} {best['avg']:.0f}ms，丢包率 {avg_loss:.1f}%",
                current=f"{avg_all:.0f}ms",
                expected="<200ms",
                details={
                    "results": latency_results,
                    "average_loss": avg_loss,
                    "best_endpoint": {"name": best["name"], "target": best["target"], "latency": best["avg"]}
                },
            )

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.PASSED,
            message=f"网络延迟正常，平均 {avg_all:.0f}ms，最佳: {best['name']} {best['avg']:.0f}ms",
            current=f"{avg_all:.0f}ms",
            expected="<200ms",
            details={
                "results": latency_results,
                "average_loss": avg_loss,
                "best_endpoint": {"name": best["name"], "target": best["target"], "latency": best["avg"]}
            },
        )

    def _is_ip(self, target: str) -> bool:
        """Check if target is an IP address"""
        try:
            socket.inet_aton(target)
            return True
        except Exception:
            return False

    def _resolve_domain(self, domain: str) -> Optional[str]:
        """Resolve domain to IP address"""
        try:
            result = socket.getaddrinfo(domain, None, socket.AF_INET)
            if result:
                return result[0][4][0]
        except Exception:
            pass
        return None

    def _ping_target(self, ip: str, original_target: str, name: str) -> Optional[Dict]:
        """Ping a target and parse result"""
        try:
            cmd = ["ping", "-n", "3", "-w", "500", ip] if subprocess.os.name == "nt" else ["ping", "-c", "3", "-W", "1", ip]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return None

            output = result.stdout

            if subprocess.os.name == "nt":
                return self._parse_windows_ping(output, original_target, name)
            else:
                return self._parse_linux_ping(output, original_target, name)

        except Exception:
            return None

    def _parse_windows_ping(self, output: str, target: str, name: str) -> Optional[Dict]:
        """Parse Windows ping output"""
        match = re.search(r"Packets:\s+Sent\s*=\s*\d+,\s+Received\s*=\s*(\d+),\s+Dumped\s*=\s*\d+,\s+Lost\s*=\s*(\d+),\s+.*?\((\d+)%\s+loss\)", output)

        loss = 100
        if match:
            received = int(match.group(1))
            lost = int(match.group(2))
            loss = (lost / (received + lost) * 100) if (received + lost) > 0 else 100

        match = re.search(r"Minimum\s*=\s*(\d+)ms,\s*Maximum\s*=\s*(\d+)ms,\s*Average\s*=\s*(\d+)ms", output)
        if match:
            return {
                "name": name,
                "target": target,
                "ip": target,
                "min": float(match.group(1)),
                "max": float(match.group(2)),
                "avg": float(match.group(3)),
                "loss": loss
            }

        match = re.search(r"Average\s*=\s*(\d+)ms", output)
        if match:
            avg = float(match.group(1))
            return {
                "name": name,
                "target": target,
                "ip": target,
                "avg": avg,
                "loss": loss
            }

        return None

    def _parse_linux_ping(self, output: str, target: str, name: str) -> Optional[Dict]:
        """Parse Linux ping output"""
        match = re.search(r"(\d+) packets transmitted,\s+(\d+) received,\s+(\d+)% packet loss", output)
        loss = 100
        if match:
            sent = int(match.group(1))
            received = int(match.group(2))
            loss = ((sent - received) / sent * 100) if sent > 0 else 100

        match = re.search(r"rtt min/avg/max/mdev\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", output)
        if match:
            return {
                "name": name,
                "target": target,
                "ip": target,
                "min": float(match.group(1)),
                "avg": float(match.group(2)),
                "max": float(match.group(3)),
                "loss": loss
            }

        match = re.search(r"min/avg/max.*?=\s*(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)", output)
        if match:
            return {
                "name": name,
                "target": target,
                "ip": target,
                "min": float(match.group(1)),
                "avg": float(match.group(2)),
                "max": float(match.group(3)),
                "loss": loss
            }

        return None
