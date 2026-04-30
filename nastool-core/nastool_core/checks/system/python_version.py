"""
checks/system/python_version.py - Python version check

Version thresholds (can also come from config_loader):
  min_version       = "3.8"
  recommended_version = "3.11"
"""

import subprocess
import shutil
import re
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check

# Hardcoded defaults (consistent with core/config_loader DEFAULT_CONFIG)
MIN_VERSION_STR = "3.8"
RECOMMENDED_VERSION_STR = "3.11"


def _command_exists(cmd: str) -> bool:
    return bool(shutil.which(cmd))


def _get_system_python_version() -> tuple:
    """Get system default Python version by running 'python3 --version'"""
    try:
        result = subprocess.run(
            ["python3", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_str = result.stdout.strip() or result.stderr.strip()
        match = re.search(r'Python (\d+)\.(\d+)\.(\d+)', version_str)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except Exception:
        pass
    return None


@register_check
class PythonVersionCheck(Check):
    """Check if Python version meets requirements"""

    check_id = "python_version"
    category = CheckCategory.SYSTEM
    title = "Python Version"
    description = "Check if Python version meets minimum requirements"

    def run(self) -> CheckResult:
        # Parse versions
        min_version = tuple(int(x) for x in MIN_VERSION_STR.split("."))
        recommended_version = tuple(int(x) for x in RECOMMENDED_VERSION_STR.split("."))

        system_version = _get_system_python_version()
        if system_version:
            current_version = system_version[:2]
            current_str = f"{current_version[0]}.{current_version[1]}"
        else:
            import sys
            current_version = sys.version_info[:2]
            current_str = f"{current_version[0]}.{current_version[1]} (fallback)"

        if current_version >= recommended_version:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"Python {current_str} meets recommended version"
        elif current_version >= min_version:
            severity = CheckSeverity.INFO
            passed = True
            message = f"Python {current_str} supported, but {RECOMMENDED_VERSION_STR} recommended"
        else:
            severity = CheckSeverity.CRITICAL
            passed = False
            message = f"Python {current_str} not supported, requires {MIN_VERSION_STR}+"

        return self._enhance_result_with_accuracy(CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current=current_str,
            expected=f"{MIN_VERSION_STR}+",
            message=message,
            fix_available=not passed,
            fix_id="install_python",
            fix_command="apt install python3.11" if _command_exists("apt") else "Install Python 3.11+",
            fix_description=f"Install Python {RECOMMENDED_VERSION_STR} or higher",
            fix_risk="low",
            url="https://www.python.org/downloads/",
        ))
