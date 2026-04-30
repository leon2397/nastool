"""
fixes/system/install_python.py - Install Python 3.11
"""

import os
import sys
from ..base import Fix, FixResult
from ..registry import register_fix


@register_fix
class InstallPythonFix(Fix):
    """Install Python 3.11 if current version is too old"""

    fix_id = "install_python"
    title = "Install Python 3.11"
    description = "Install Python 3.11+ if current version is below 3.8"
    risk = "medium"
    requires_root = True

    def is_applicable(self) -> bool:
        """Check if Python upgrade is needed"""
        current = sys.version_info[:2]
        return current < (3, 8)

    def run(self) -> FixResult:
        commands_run = []

        # Detect package manager
        if self._run_command("which apt")[0]:
            # Debian/Ubuntu
            commands = [
                "apt update",
                "apt install -y python3.11 python3.11-venv python3.11-dev python3-pip",
                "update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1",
            ]
        elif self._run_command("which yum")[0]:
            # CentOS/RHEL
            commands = [
                "yum install -y python3.11 python3.11-pip",
                "alternatives --set python3 /usr/bin/python3.11",
            ]
        elif self._run_command("which dnf")[0]:
            # Fedora
            commands = [
                "dnf install -y python3.11 python3.11-pip",
                "alternatives --set python3 /usr/bin/python3.11",
            ]
        else:
            return FixResult(
                fix_id=self.fix_id,
                success=False,
                message="Unsupported package manager. Please install Python 3.11+ manually.",
                commands_run=commands_run,
            )

        # Run installation commands
        for cmd in commands:
            success, output = self._run_command(cmd, timeout=300)
            commands_run.append(cmd)

            if not success:
                return FixResult(
                    fix_id=self.fix_id,
                    success=False,
                    message=f"Failed to execute: {cmd}",
                    commands_run=commands_run,
                    output=output,
                )

        return FixResult(
            fix_id=self.fix_id,
            success=True,
            message="Python 3.11 installed successfully. Please restart the script.",
            commands_run=commands_run,
        )
