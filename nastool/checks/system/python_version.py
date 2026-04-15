"""
checks/system/python_version.py - Python version check
"""

import sys
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check
from core.config_loader import get_config


@register_check
class PythonVersionCheck(Check):
    """Check if Python version meets requirements"""

    check_id = "python_version"
    category = CheckCategory.SYSTEM
    title = "Python Version"
    description = "Check if Python version meets minimum requirements"

    def run(self) -> CheckResult:
        # 从配置读取阈值
        config = get_config()
        min_version_str = config.system.python_min_version
        recommended_version_str = config.system.python_recommended_version

        # 解析版本
        min_version = tuple(int(x) for x in min_version_str.split("."))
        recommended_version = tuple(int(x) for x in recommended_version_str.split("."))

        current_version = sys.version_info[:2]
        current_str = f"{current_version[0]}.{current_version[1]}"

        if current_version >= recommended_version:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"Python {current_str} meets recommended version"
        elif current_version >= min_version:
            severity = CheckSeverity.INFO
            passed = True
            message = f"Python {current_str} supported, but {recommended_version_str} recommended"
        else:
            severity = CheckSeverity.CRITICAL
            passed = False
            message = f"Python {current_str} not supported, requires {min_version_str}+"

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current=current_str,
            expected=f"{min_version_str}+",
            message=message,
            fix_available=not passed,
            fix_id="install_python",
            fix_command="apt install python3.11"
            if self._command_exists("apt")
            else "Install Python 3.11+",
            fix_description=f"Install Python {recommended_version_str} or higher",
            fix_risk="low",
            url="https://www.python.org/downloads/",
        )
