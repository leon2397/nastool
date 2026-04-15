"""
checks/storage/disk_space.py - Check available disk space
"""

import shutil
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class DiskSpaceCheck(Check):
    """Check available disk space for NAS storage"""

    check_id = "disk_space"
    title = "Disk Space"
    description = "Check available disk space meets NAS requirements"
    category = CheckCategory.STORAGE

    def run(self) -> CheckResult:
        """Run disk space check"""
        # Get disk usage
        total, used, free = shutil.disk_usage("/")

        total_gb = total / (1024**3)
        free_gb = free / (1024**3)
        free_percent = (free / total) * 100

        # Check thresholds
        if free_gb < 10:
            severity = CheckSeverity.CRITICAL
            passed = False
            message = f"Critical: Only {free_gb:.1f}GB free space (< 10GB)"
            fix = "Clean up old files or expand storage"
        elif free_gb < 50:
            severity = CheckSeverity.WARNING
            passed = True
            message = f"Warning: Only {free_gb:.1f}GB free space (< 50GB)"
            fix = "Consider cleaning up old files"
        elif free_percent < 10:
            severity = CheckSeverity.WARNING
            passed = True
            message = f"Warning: Disk {free_percent:.1f}% free (< 10%)"
            fix = "Consider expanding storage"
        else:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"{free_gb:.1f}GB free ({free_percent:.1f}%)"
            fix = None

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=passed,
            severity=severity,
            message=message,
            current=f"{free_gb:.1f}GB / {total_gb:.1f}GB ({free_percent:.1f}%)",
            expected="≥50GB free or ≥10% free",
            fix_available=fix is not None,
            fix_description=fix,
        )
