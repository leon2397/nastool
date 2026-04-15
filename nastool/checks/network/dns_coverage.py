from typing import Optional
"""
checks/network/dns_coverage.py - DNS coverage check
检查 DNS 配置覆盖是否充分
"""

import subprocess
import re
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class DNSCoverageCheck(Check):
    """Check DNS resolver coverage"""

    check_id = "dns_coverage"
    title = "DNS 覆盖检测"
    description = "检查 /etc/resolv.conf DNS 服务器数量和覆盖质量"
    category = CheckCategory.NETWORK

    # 最低要求
    MIN_NS_COUNT = 2
    RECOMMENDED_NS_COUNT = 3

    # 推荐 DNS
    RECOMMENDED = {"8.8.8.8", "8.8.4.4", "223.5.5.5", "223.6.6.6", "1.1.1.1", "1.0.0.1"}

    def run(self) -> CheckResult:
        """Run DNS coverage check"""
        dns_info = self._parse_resolv_conf()

        if dns_info is None:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message="无法读取 /etc/resolv.conf",
                current="无法读取",
                expected="至少配置 2 个 DNS 服务器",
                fix_available=True,
                fix_description="创建 /etc/resolv.conf 并配置 DNS 服务器（如 223.5.5.5 和 8.8.8.8）",
                fix_command="echo 'nameserver 223.5.5.5' >> /etc/resolv.conf && echo 'nameserver 8.8.8.8' >> /etc/resolv.conf",
            )

        nameservers = dns_info.get("nameservers", [])
        count = len(nameservers)

        # 推荐 DNS 覆盖
        recommended_used = [ns for ns in nameservers if ns in self.RECOMMENDED]
        recommended_count = len(recommended_used)

        # 解析速度测试（抽查最快 DNS）
        fastest = self._test_dns_speeds(nameservers)

        if count == 0:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.CRITICAL,
                message="未配置任何 DNS 服务器",
                current="0 个 nameserver",
                expected=f">= {self.MIN_NS_COUNT} 个 nameserver",
                fix_available=True,
                fix_description="配置至少 2 个可靠的公共 DNS 服务器",
            )

        if count == 1:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message=f"仅配置 1 个 DNS 服务器（单点故障风险）",
                current=f"1 个: {', '.join(nameservers)}",
                expected=f">= {self.MIN_NS_COUNT} 个 DNS 服务器",
                fix_available=True,
                fix_description="追加至少 1 个备用 DNS 服务器（如 223.5.5.5）",
                fix_command="echo 'nameserver 223.5.5.5' >> /etc/resolv.conf",
            )

        if count >= self.RECOMMENDED_NS_COUNT:
            msg = f"DNS 配置完善（{count} 个）"
            if recommended_count > 0:
                msg += f"，含 {recommended_count} 个推荐 DNS"
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.PASSED,
                message=msg,
                current=f"{count} 个: {', '.join(nameservers)}",
                expected=f">= {self.RECOMMENDED_NS_COUNT} 个",
                details={"nameservers": nameservers, "recommended": recommended_used},
            )

        # 2个（刚好够）
        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=True,
            severity=CheckSeverity.WARNING,
            message=f"DNS 配置基本够用，但建议增加到 {self.RECOMMENDED_NS_COUNT} 个",
            current=f"{count} 个: {', '.join(nameservers)}",
            expected=f">= {self.RECOMMENDED_NS_COUNT} 个",
            details={"nameservers": nameservers},
        )

    def _parse_resolv_conf(self) -> Optional[dict]:
        """Parse /etc/resolv.conf"""
        try:
            with open("/etc/resolv.conf", "r") as f:
                content = f.read()
            nameservers = re.findall(r"^nameserver\s+(\S+)", content, re.MULTILINE)
            return {"nameservers": nameservers, "path": "/etc/resolv.conf"}
        except FileNotFoundError:
            return None
        except Exception:
            return None

    def _test_dns_speeds(self, nameservers: list) -> list:
        """Test DNS resolution speeds"""
        results = []
        for ns in nameservers[:3]:  # 最多测3个
            speed = self._ping_dns(ns)
            results.append({"ns": ns, "ms": speed})
        return results

    def _ping_dns(self, ns: str) -> float:
        """Ping a DNS server to measure response time"""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", ns],
                capture_output=True, text=True, timeout=3,
            )
            # 解析: time=12.3 ms
            match = re.search(r"time[=<]?(\d+\.?\d*)\s*ms", result.stdout, re.IGNORECASE)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return -1
