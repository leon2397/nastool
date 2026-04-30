"""
fixes/base.py - Base classes for all fixes
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class FixResult:
    """Result of a fix execution"""

    fix_id: str  # Fix identifier
    success: bool  # True if fix succeeded
    message: str  # Human-readable result message
    changed_files: List[str] = field(default_factory=list)  # Files modified
    commands_run: List[str] = field(default_factory=list)  # Commands executed
    rollback_command: Optional[str] = None  # Command to undo the fix
    error: Optional[str] = None  # Error message if failed
    output: Optional[str] = None  # Command output


class Fix(ABC):
    """Abstract base class for all fixes"""

    # Subclasses should override these
    fix_id: str = "base_fix"
    title: str = "Base Fix"
    description: str = "Base fix class"
    risk: str = "low"  # low / medium / high
    requires_root: bool = False

    @abstractmethod
    def is_applicable(self) -> bool:
        """
        Check if this fix is applicable.

        Returns:
            True if the fix can be applied
        """
        pass

    @abstractmethod
    def run(self) -> FixResult:
        """
        Execute the fix.

        Returns:
            FixResult with execution details
        """
        pass

    def _run_command(self, cmd: str, timeout: int = 60) -> tuple:
        """
        Run shell command.

        Returns:
            (success, output) tuple
        """
        import subprocess

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def _check_root(self) -> bool:
        """Check if running as root (cross-platform: Unix + Windows)"""
        import os, sys

        try:
            # Unix/Linux/macOS
            return os.geteuid() == 0
        except AttributeError:
            # Windows: check via ctypes
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                return False

    def _confirm(self, message: str) -> bool:
        """
        Ask user for confirmation.

        Args:
            message: Confirmation prompt

        Returns:
            True if user confirms
        """
        try:
            response = input(f"{message} [y/N]: ").strip().lower()
            return response in ["y", "yes"]
        except EOFError:
            return False
