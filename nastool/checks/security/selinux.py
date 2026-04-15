"""
checks/security/selinux.py - Check SELinux configuration
"""

import subprocess
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class SELinuxCheck(Check):
    """Check SELinux is configured for NAS"""

    check_id = "selinux"
    title = "SELinux Configuration"
    description = "Check SELinux allows NAS operations"
    category = CheckCategory.SECURITY

    def run(self) -> CheckResult:
        """Run SELinux check"""
        try:
            result = subprocess.run(["getenforce"], capture_output=True, text=True, timeout=5)

            status = result.stdout.strip().lower()

            if status == "disabled":
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=True,
                    severity=CheckSeverity.INFO,
                    message="SELinux is disabled",
                    current="Disabled",
                    expected="Permissive or Disabled for NAS",
                )

            if status == "permissive":
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=True,
                    severity=CheckSeverity.PASSED,
                    message="SELinux is permissive (logs only)",
                    current="Permissive",
                    expected="Permissive for NAS compatibility",
                )

            if status == "enforcing":
                return CheckResult(
                    check_id=self.check_id,
                    title=self.title,
                    category=self.category,
                    passed=False,
                    severity=CheckSeverity.WARNING,
                    message="SELinux is enforcing (may block NAS operations)",
                    current="Enforcing",
                    expected="Permissive for NAS compatibility",
                    fix_available=True,
                    fix_description="Set SELinux to permissive",
                    fix_command="setenforce 0",
                )

            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"SELinux status: {status}",
                current=status,
                expected="Permissive or Disabled",
            )

        except FileNotFoundError:
            # SELinux not installed
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.PASSED,
                message="SELinux not installed",
                current="Not installed",
                expected="Not required",
            )
        except Exception as e:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"Could not check SELinux: {str(e)}",
                current="Unknown",
                expected="Permissive or Disabled",
            )
