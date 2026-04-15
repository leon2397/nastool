"""
fixes/storage/create_paths.py - Create missing NAS storage paths
"""

import os
from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class CreatePathsFix(Fix):
    """Create missing NAS storage directories"""

    fix_id = "create_paths"
    title = "Create Storage Paths"
    description = "Create missing NAS storage directories"
    risk = "low"
    requires_root = False

    def is_applicable(self) -> bool:
        """Check if paths need to be created"""
        # Always applicable - check will determine what's needed
        return True

    def run(self, paths=None) -> FixResult:
        """Create missing paths"""
        from checks.storage.path_exists import PathExistsCheck

        # Get default paths if not specified
        if paths is None:
            paths = PathExistsCheck.DEFAULT_PATHS

        commands_run = []
        created = []
        failed = []

        for path in paths:
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                    commands_run.append(f"mkdir -p {path}")
                    created.append(path)
                except Exception as e:
                    failed.append(f"{path}: {str(e)}")

        if failed:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message=f"Created {len(created)} paths, failed {len(failed)}: {', '.join(failed[:3])}",
                commands_run=commands_run,
            )

        if created:
            return FixResult(
                fix_id=self.fix_id,
                success=True,
                message=f"Created {len(created)} paths: {', '.join(created[:5])}",
                commands_run=commands_run,
            )
        else:
            return FixResult(
                fix_id=self.fix_id,
                success=True,
                message="All paths already exist",
                commands_run=commands_run,
            )
