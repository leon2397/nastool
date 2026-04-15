"""
checks/network/internet_access.py - Internet connectivity check
"""

import socket
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class InternetAccessCheck(Check):
    """Check internet connectivity"""

    check_id = "internet_access"
    category = CheckCategory.NETWORK
    title = "Internet Access"
    description = "Check if device can reach the internet"

    TEST_HOSTS = [
        ("baidu.com", 80),
        ("google.com", 80),
        ("github.com", 443),
    ]

    def _can_reach(self, host: str, port: int, timeout: float = 5.0) -> bool:
        """Test if we can reach a host:port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            return False

    def run(self) -> CheckResult:
        reachable = []
        unreachable = []

        for host, port in self.TEST_HOSTS:
            if self._can_reach(host, port):
                reachable.append(host)
            else:
                unreachable.append(host)

        if reachable:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"Internet reachable via: {', '.join(reachable)}"
        else:
            severity = CheckSeverity.CRITICAL
            passed = False
            message = "No internet access detected"

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current="connected" if passed else "disconnected",
            expected="connected",
            message=message,
            fix_available=not passed,
            fix_id="fix_network",
            fix_description="Check network gateway, DNS, or firewall settings",
            fix_risk="medium",
            details={"reachable": reachable, "unreachable": unreachable},
        )
