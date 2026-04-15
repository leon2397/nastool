"""
checks/storage/path_exists.py - Check NAS storage paths exist
"""

import os
from ..base import Check, CheckResult, CheckSeverity, CheckCategory
from ..registry import register_check


@register_check
class PathExistsCheck(Check):
    """Check required NAS storage paths exist"""

    check_id = "path_exists"
    title = "Storage Paths"
    description = "Check NAS storage paths are configured"
    category = CheckCategory.STORAGE

    # Default NAS paths to check
    DEFAULT_PATHS = [
        "/nas",
        "/nas/media",
        "/nas/photos",
        "/nas/videos",
    ]

    def run(self, paths=None) -> CheckResult:
        """Run path existence check"""
        paths = paths or self.DEFAULT_PATHS

        missing = []
        existing = []

        for path in paths:
            if os.path.exists(path):
                existing.append(path)
            else:
                missing.append(path)

        if not missing:
            return CheckResult(
                check_id=self.check_id,
                title=self.title,
                category=self.category,
                passed=True,
                severity=CheckSeverity.PASSED,
                message=f"All {len(existing)} paths exist",
                current=f"{len(existing)}/{len(paths)} paths",
                expected="All paths exist",
            )

        # Some paths missing
        if existing:
            severity = CheckSeverity.WARNING
            message = f"Missing {len(missing)}/{len(paths)} paths: {', '.join(missing[:3])}"
        else:
            severity = CheckSeverity.CRITICAL
            message = f"No NAS paths found. Missing: {', '.join(missing[:3])}"

        return CheckResult(
            check_id=self.check_id,
            title=self.title,
            category=self.category,
            passed=False,
            severity=severity,
            message=message,
            current=f"{len(existing)}/{len(paths)} paths",
            expected="All paths exist",
            fix_available=True,
            fix_description="Create missing directories",
            fix_command=f"mkdir -p {' '.join(missing)}",
        )
