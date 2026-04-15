"""
checks/system/pip_installed.py - pip availability check
"""

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class PipInstalledCheck(Check):
    """Check if pip is installed"""

    check_id = "pip_installed"
    category = CheckCategory.SYSTEM
    title = "pip Installed"
    description = "Check if pip package manager is available"

    def run(self) -> CheckResult:
        pip_exists = self._command_exists("pip3") or self._command_exists("pip")

        # Try to get pip version
        pip_version = ""
        if self._command_exists("pip3"):
            pip_version = self._run_command("pip3 --version 2>/dev/null | head -1")
        elif self._command_exists("pip"):
            pip_version = self._run_command("pip --version 2>/dev/null | head -1")

        if pip_exists:
            severity = CheckSeverity.PASSED
            passed = True
            message = (
                f"pip is available: {pip_version.split()[1] if pip_version else 'unknown version'}"
            )
        else:
            severity = CheckSeverity.CRITICAL
            passed = False
            message = "pip is not installed, cannot install Python packages"

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current="installed" if pip_exists else "not installed",
            expected="installed",
            message=message,
            fix_available=not passed,
            fix_id="install_pip",
            fix_command="apt install python3-pip" if self._command_exists("apt") else "Install pip",
            fix_description="Install pip package manager",
            fix_risk="low",
        )
