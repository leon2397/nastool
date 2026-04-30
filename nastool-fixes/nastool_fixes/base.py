"""
fixes/base.py - Base classes for all fixes (v2.0 - Security Framework)

安全准则：零破坏、零篡改、所有操作可撤销
- 所有 fix 执行前必须通过 SecurityPolicy 检查
- 禁止清单硬编码屏蔽（FORBIDDEN_FIXES）
- 强制 dry_run + backup 流程
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from pathlib import Path


@dataclass
class FixResult:
    """Result of a fix execution (v2.0 - Security Enhanced)"""

    fix_id: str  # Fix identifier
    success: bool  # True if fix succeeded
    message: str  # Human-readable result message
    changed_files: List[str] = field(default_factory=list)  # Files modified
    commands_run: List[str] = field(default_factory=list)  # Commands executed
    rollback_command: Optional[str] = None  # Command to undo the fix
    rollback_script: Optional[str] = None  # Path to rollback script (v2.0)
    backup_files: List[str] = field(default_factory=list)  # Backup files created (v2.0)
    dry_run: bool = False  # Was this a dry-run? (v2.0)
    blocked: bool = False  # Was blocked by security policy? (v2.0)
    block_reason: Optional[str] = None  # Block reason if blocked (v2.0)
    error: Optional[str] = None  # Error message if failed
    output: Optional[str] = None  # Command output


class Fix(ABC):
    """Abstract base class for all fixes (v2.0 - Security Enhanced)"""

    # Subclasses should override these
    fix_id: str = "base_fix"
    title: str = "Base Fix"
    description: str = "Base fix class"
    risk: str = "low"  # low / medium / high / danger
    requires_root: bool = False
    
    # v2.0: 安全框架强制参数
    _policy = None
    _backup_mgr = None

    @abstractmethod
    def is_applicable(self) -> bool:
        """
        Check if this fix is applicable.

        Returns:
            True if the fix can be applied
        """
        pass

    def _init_security(self):
        """初始化安全框架（延迟加载）"""
        if self._policy is None:
            # Import from security.py file
            import importlib.util
            import os
            import sys
            
            # Add current directory to path
            sys.path.insert(0, os.path.dirname(__file__))
            
            # Import security module from security.py
            security_spec = importlib.util.spec_from_file_location("security", os.path.join(os.path.dirname(__file__), "security.py"))
            security_module = importlib.util.module_from_spec(security_spec)
            security_spec.loader.exec_module(security_module)
            
            self._policy = security_module.get_policy()
        if self._backup_mgr is None:
            # Import from security.py file
            import importlib.util
            import os
            import sys
            
            # Add current directory to path
            sys.path.insert(0, os.path.dirname(__file__))
            
            # Import security module from security.py
            security_spec = importlib.util.spec_from_file_location("security", os.path.join(os.path.dirname(__file__), "security.py"))
            security_module = importlib.util.module_from_spec(security_spec)
            security_spec.loader.exec_module(security_module)
            
            self._backup_mgr = security_module.get_backup_manager()

    def check_security(self) -> Tuple[bool, str]:
        """
        检查是否允许执行此 fix。

        Returns:
            (allowed, message): allowed=True 表示可以执行
        """
        self._init_security()
        return self._policy.check_fix(self.fix_id, self.risk)

    def is_forbidden(self) -> bool:
        """检查是否在禁止清单中"""
        self._init_security()
        return self._policy.is_forbidden(self.fix_id)

    def get_forbidden_reason(self) -> str:
        """获取禁止原因"""
        self._init_security()
        return self._policy.get_forbidden_reason(self.fix_id)

    @abstractmethod
    def run(self, dry_run: bool = False) -> FixResult:
        """
        Execute the fix.

        Args:
            dry_run: If True, show what would happen without executing

        Returns:
            FixResult with execution details
        """
        pass

    def preview(self) -> FixResult:
        """
        Preview what this fix would do (dry-run mode).

        Returns:
            FixResult with dry_run=True and preview information
        """
        return self.run(dry_run=True)

    def execute_safe(self, dry_run: bool = False, force: bool = False) -> FixResult:
        """
        Safe execution with full security checks.

        Flow: security check → dry_run preview → backup → execute → rollback script

        Args:
            dry_run: If True, only preview without executing
            force: Skip security check (DANGEROUS, only for testing)

        Returns:
            FixResult
        """
        self._init_security()

        # 1. Security check (cannot be skipped unless force=True)
        if not force:
            allowed, msg = self.check_security()
            if not allowed:
                return FixResult(
                    fix_id=self.fix_id,
                    success=False,
                    message=msg,
                    blocked=True,
                    block_reason=msg,
                    dry_run=dry_run,
                )

        # 2. Dry-run mode: just preview
        if dry_run:
            return self.preview()

        # 3. Execute with backup
        return self.run(dry_run=False)

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
