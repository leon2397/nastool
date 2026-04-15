"""
checks/security/firewall.py - Check firewall configuration
"""

import subprocess
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class FirewallCheck(Check):
    """Check firewall allows NAS ports"""

    check_id = "firewall"
    title = "Firewall Configuration"
    description = "Check firewall allows NAS service ports"
    category = CheckCategory.SECURITY

    NAS_PORTS = [8000, 443, 80]

    def run(self) -> CheckResult:
        """Run firewall check"""
        # Check if ufw is available
        try:
            result = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=5)

            if "inactive" in result.stdout:
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=True,
                    severity=CheckSeverity.WARNING,
                    message="Firewall is inactive (all ports open)",
                    current="ufw inactive",
                    expected="ufw active with NAS ports allowed",
                    fix_available=True,
                    fix_description="Enable firewall and allow NAS ports",
                    fix_command="ufw allow 8000/tcp && ufw allow 443/tcp && ufw allow 80/tcp && ufw enable",
                )

            # Check if NAS ports are allowed
            allowed_ports = []
            for port in self.NAS_PORTS:
                if f"{port}" in result.stdout:
                    allowed_ports.append(port)

            if len(allowed_ports) == len(self.NAS_PORTS):
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=True,
                    severity=CheckSeverity.PASSED,
                    message=f"All NAS ports allowed: {allowed_ports}",
                    current=f"Ports {allowed_ports} allowed",
                    expected="NAS ports allowed",
                )
            else:
                missing = [p for p in self.NAS_PORTS if p not in allowed_ports]
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=False,
                    severity=CheckSeverity.WARNING,
                    message=f"Missing ports: {missing}",
                    current=f"Ports {allowed_ports} allowed",
                    expected="All NAS ports allowed",
                    fix_available=True,
                    fix_description=f"Allow ports: {missing}",
                )

        except FileNotFoundError:
            # ufw not installed
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="ufw not installed (no firewall detected)",
                current="No firewall",
                expected="Firewall recommended for production",
            )
        except Exception as e:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"Could not check firewall: {str(e)}",
                current="Unknown",
                expected="Firewall recommended",
            )
