"""
checks/network/dns_resolve.py - DNS resolution check
"""

import socket
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class DNSResolveCheck(Check):
    """Check DNS resolution capability"""

    check_id = "dns_resolve"
    category = CheckCategory.NETWORK
    title = "DNS Resolution"
    description = "Check if DNS resolution works"

    TEST_DOMAINS = ["baidu.com", "google.com", "github.com"]

    def run(self) -> CheckResult:
        resolved = []
        failed = []

        for domain in self.TEST_DOMAINS:
            try:
                ip = socket.gethostbyname(domain)
                resolved.append({"domain": domain, "ip": ip})
            except socket.gaierror:
                failed.append(domain)

        # Check DNS config
        dns_servers = []
        try:
            with open("/etc/resolv.conf", "r") as f:
                for line in f:
                    if line.startswith("nameserver"):
                        dns_servers.append(line.split()[1])
        except Exception as e:
            pass  # TODO: 添加日志

        if not failed:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"DNS resolution working for all test domains"
        else:
            severity = CheckSeverity.CRITICAL
            passed = False
            message = f"DNS resolution failed for: {', '.join(failed)}"

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current="working" if passed else "failed",
            expected="working",
            message=message,
            fix_available=not passed,
            fix_id="fix_dns",
            fix_command="echo 'nameserver 8.8.8.8' | sudo tee /etc/resolv.conf",
            fix_description="Configure DNS to use 8.8.8.8 (Google DNS)",
            fix_risk="low",
            details={
                "resolved": resolved,
                "failed": failed,
                "dns_servers": dns_servers,
            },
        )
