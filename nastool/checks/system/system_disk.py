"""
checks/system/disk_space.py - Disk space check
"""

import shutil
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class DiskSpaceCheck(Check):
    """Check available disk space"""

    check_id = "disk_space"
    category = CheckCategory.SYSTEM
    title = "Disk Space"
    description = "Check if disk has enough free space"

    MIN_SPACE_GB = 5
    RECOMMENDED_SPACE_GB = 50

    def run(self) -> CheckResult:
        # Get disk usage for current directory
        try:
            usage = shutil.disk_usage(".")
            total_gb = usage.total // (1024**3)
            free_gb = usage.free // (1024**3)
            used_percent = (usage.used / usage.total) * 100
        except Exception as e:
            total_gb = 0
            free_gb = 0
            used_percent = 0

        if free_gb >= self.RECOMMENDED_SPACE_GB:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"Disk {free_gb}GB free of {total_gb}GB total ({used_percent:.1f}% used)"
        elif free_gb >= self.MIN_SPACE_GB:
            severity = CheckSeverity.WARNING
            passed = True
            message = f"Disk {free_gb}GB free, {self.RECOMMENDED_SPACE_GB}GB recommended"
        else:
            severity = CheckSeverity.CRITICAL
            passed = False
            message = f"Disk {free_gb}GB free, below minimum {self.MIN_SPACE_GB}GB"

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current=f"{free_gb}GB free",
            expected=f">= {self.MIN_SPACE_GB}GB",
            message=message,
            fix_available=False,
            fix_description="Clean up files or expand disk"
            if free_gb < self.MIN_SPACE_GB
            else None,
            fix_risk="none",
            details={
                "total_gb": total_gb,
                "free_gb": free_gb,
                "used_percent": round(used_percent, 1),
            },
        )
