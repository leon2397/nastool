"""
checks/security/ssh_root.py - Check SSH root login configuration
"""

import subprocess
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class SSHRootCheck(Check):
    """Check SSH root login is disabled"""

    check_id = "ssh_root"
    title = "SSH Root Login"
    description = "Check SSH root login is disabled for security"
    category = CheckCategory.SECURITY

    def run(self) -> CheckResult:
        """Run SSH root login check"""
        sshd_config = "/etc/ssh/sshd_config"

        try:
            with open(sshd_config, "r") as f:
                content = f.read()

            # Check PermitRootLogin
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("PermitRootLogin"):
                    value = line.split()[-1].lower()

                    if value in ["no", "prohibit-password"]:
                        return CheckResult(
                            check_id=self.check_id,
                            title=self.title,
                            category=self.category,
                            passed=True,
                            severity=CheckSeverity.PASSED,
                            message=f"Root login is {value}",
                            current=value,
                            expected="no or prohibit-password",
                        )

                    if value == "yes":
                        return CheckResult(
                            check_id=self.check_id,
                            title=self.title,
                            category=self.category,
                            passed=False,
                            severity=CheckSeverity.WARNING,
                            message="Root login is enabled (security risk)",
                            current="yes",
                            expected="no or prohibit-password",
                            fix_available=True,
                            fix_description="Disable SSH root login",
                            fix_command="sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config",
                        )

            # Default: PermitRootLogin not set (usually yes)
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=False,
                severity=CheckSeverity.WARNING,
                message="PermitRootLogin not set (default: yes)",
                current="Not set (default yes)",
                expected="no or prohibit-password",
                fix_available=True,
                fix_description="Set PermitRootLogin no",
            )

        except FileNotFoundError:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message="sshd_config not found (not an SSH server)",
                current="N/A",
                expected="N/A",
            )
        except Exception as e:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.INFO,
                message=f"Could not check SSH config: {str(e)}",
                current="Unknown",
                expected="no or prohibit-password",
            )
