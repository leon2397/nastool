"""
checks/system/system_libs.py - System library dependencies check
"""

import os
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class SystemLibsCheck(Check):
    """Check for required system libraries"""

    check_id = "system_libs"
    category = CheckCategory.SYSTEM
    title = "System Libraries"
    description = "Check for required system libraries (ssl, sqlite, etc.)"

    REQUIRED_LIBS = {
        "ssl": {"check": "libssl", "package": "libssl-dev", "description": "OpenSSL library"},
        "sqlite3": {
            "check": "libsqlite3",
            "package": "libsqlite3-dev",
            "description": "SQLite library",
        },
        "ffi": {"check": "libffi", "package": "libffi-dev", "description": "FFI library"},
        "zlib": {"check": "libz", "package": "zlib1g-dev", "description": "Zlib compression"},
    }

    def _check_library(self, lib_name: str) -> bool:
        """Check if a library is available"""
        # Try ldconfig
        result = self._run_command(f"ldconfig -p 2>/dev/null | grep -i {lib_name}")
        if result:
            return True

        # Try pkg-config
        result = self._run_command(f"pkg-config --exists {lib_name} 2>/dev/null && echo ok")
        if result:
            return True

        return False

    def run(self) -> CheckResult:
        missing = []
        found = []

        for lib_key, lib_info in self.REQUIRED_LIBS.items():
            if self._check_library(lib_info["check"]):
                found.append(lib_key)
            else:
                missing.append(lib_key)

        if not missing:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"All required libraries available: {', '.join(found)}"
        else:
            severity = CheckSeverity.WARNING
            passed = True  # Not critical, some features may not work
            message = f"Missing libraries: {', '.join(missing)}. Some features may not work."

        apt_packages = [self.REQUIRED_LIBS[m]["package"] for m in missing]

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current=f"{len(found)}/{len(self.REQUIRED_LIBS)} available",
            expected="all available",
            message=message,
            fix_available=len(missing) > 0,
            fix_id="install_system_libs",
            fix_command=f"apt install {' '.join(apt_packages)}"
            if apt_packages and self._command_exists("apt")
            else None,
            fix_description=f"Install missing libraries: {', '.join(missing)}" if missing else None,
            fix_risk="low",
            details={"missing": missing, "found": found},
        )
