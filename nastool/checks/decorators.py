# -*- coding: utf-8 -*-
"""
checks/decorators.py - Declarative check definition via @check() decorator

Usage (new style — function-based):
    from checks.decorators import check, CheckContext

    @check(
        id="tensorflow_version",
        category=CheckCategory.AI,
        severity=CheckSeverity.WARNING,
        timeout=10,
        depends_on=["gpu_detected"],
    )
    def tensorflow_version(ctx: CheckContext) -> CheckResult:
        '''Check TensorFlow version'''
        try:
            import tensorflow as tf
            version = tf.__version__
            return ctx.passed(
                current=version,
                expected="latest",
                message=f"TensorFlow {version}",
                details={"version": version},
            )
        except ImportError:
            return ctx.failed(
                current="not installed",
                expected="installed",
                message="TensorFlow not installed",
                fix_id="install_tensorflow",
                fix_command="pip install tensorflow",
                fix_description="Install TensorFlow",
            )

Old style (class-based) still works — no breaking changes.
"""

from __future__ import annotations

import functools
from typing import Callable, List, Optional

from .base import Check, CheckResult, CheckCategory, CheckSeverity


class CheckContext:
    """
    Helper context passed to function-based checks.
    Provides convenience methods for common operations.
    """

    __slots__ = ("check_id", "category", "severity", "title", "description",
                 "timeout", "depends_on", "tags", "can_parallel")

    def __init__(
        self,
        check_id: str,
        category: CheckCategory,
        severity: CheckSeverity,
        title: str,
        description: str = "",
        timeout: float = 30.0,
        depends_on: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        can_parallel: bool = True,
    ):
        self.check_id = check_id
        self.category = category
        self.severity = severity
        self.title = title
        self.description = description
        self.timeout = timeout
        self.depends_on = depends_on or []
        self.tags = tags or []
        self.can_parallel = can_parallel

    # ── Result builders ──────────────────────────────────────────────

    def passed(
        self,
        current: str = "",
        expected: str = "",
        message: str = "",
        severity: Optional[CheckSeverity] = None,
        details: Optional[dict] = None,
        **kwargs,
    ) -> CheckResult:
        """Build a passing CheckResult."""
        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity or CheckSeverity.PASSED,
            passed=True,
            title=self.title,
            current=current,
            expected=expected,
            message=message,
            details=details or {},
            **kwargs,
        )

    def failed(
        self,
        current: str = "",
        expected: str = "",
        message: str = "",
        severity: Optional[CheckSeverity] = None,
        fix_available: bool = False,
        fix_id: Optional[str] = None,
        fix_command: Optional[str] = None,
        fix_description: Optional[str] = None,
        fix_risk: str = "low",
        details: Optional[dict] = None,
        **kwargs,
    ) -> CheckResult:
        """Build a failing CheckResult."""
        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity or self.severity,
            passed=False,
            title=self.title,
            current=current,
            expected=expected,
            message=message,
            fix_available=fix_available,
            fix_id=fix_id,
            fix_command=fix_command,
            fix_description=fix_description,
            fix_risk=fix_risk,
            details=details or {},
            **kwargs,
        )

    def warning(
        self,
        current: str = "",
        expected: str = "",
        message: str = "",
        details: Optional[dict] = None,
        **kwargs,
    ) -> CheckResult:
        """Build a warning (passed=True but attention needed)."""
        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=CheckSeverity.WARNING,
            passed=True,
            title=self.title,
            current=current,
            expected=expected,
            message=message,
            details=details or {},
            **kwargs,
        )

    def info(
        self,
        current: str = "",
        expected: str = "",
        message: str = "",
        details: Optional[dict] = None,
        **kwargs,
    ) -> CheckResult:
        """Build an informational CheckResult."""
        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=CheckSeverity.INFO,
            passed=True,
            title=self.title,
            current=current,
            expected=expected,
            message=message,
            details=details or {},
            **kwargs,
        )

    def skipped(
        self,
        reason: str = "skipped",
        message: str = "",
    ) -> CheckResult:
        """Build a skipped CheckResult (treated as passed/info)."""
        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=CheckSeverity.INFO,
            passed=True,
            title=self.title,
            current="skipped",
            expected="not_run",
            message=message or f"Skipped: {reason}",
            details={"skip_reason": reason},
        )

    # ── System helpers (delegate to Check base methods) ──────────────

    def run_command(self, cmd: str, timeout: int = 10) -> str:
        """Run a shell command and return stdout."""
        import subprocess
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def read_file(self, path: str) -> str:
        """Read file contents."""
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception:
            return ""

    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        import os
        return os.path.exists(path)

    def command_exists(self, cmd: str) -> bool:
        """Check if command is available."""
        import shutil
        return shutil.which(cmd) is not None


def _id_to_class_name(check_id: str) -> str:
    """Convert snake_case check_id to PascalCase class name with Check suffix.
    e.g. 'tensorflow_version' -> 'TensorFlowVersionCheck'
    """
    parts = check_id.split("_")
    return "".join(p.capitalize() for p in parts) + "Check"


def check(
    id: str,
    category: CheckCategory,
    severity: CheckSeverity = CheckSeverity.WARNING,
    title: Optional[str] = None,
    description: str = "",
    timeout: float = 30.0,
    depends_on: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    can_parallel: bool = True,
    class_name: Optional[str] = None,
):
    """
    Decorator to declare a function-based check.

    Wraps a plain function into a Check subclass that is auto-registered
    in the check registry.  The function receives a CheckContext and must
    return a CheckResult.

    Example:
        @check(id="gpu_detected", category=CheckCategory.AI)
        def gpu_detected(ctx: CheckContext) -> CheckResult:
            if ctx.file_exists("/dev/nvidia0"):
                return ctx.passed(current="detected", message="GPU found")
            return ctx.warning(current="none", message="No GPU detected")
    """

    def decorator(fn: Callable[[CheckContext], CheckResult]) -> type:
        # Build a human-friendly title from function name if not provided
        _title = title or fn.__name__.replace("_", " ").title()
        _description = description or fn.__doc__ or _title
        _depends_on = depends_on or []
        _tags = tags or []
        _class_name = class_name or _id_to_class_name(id)

        # Create CheckContext instance (shared metadata)
        ctx = CheckContext(
            check_id=id,
            category=category,
            severity=severity,
            title=_title,
            description=_description,
            timeout=timeout,
            depends_on=_depends_on,
            tags=_tags,
            can_parallel=can_parallel,
        )

        # Capture closure values to avoid class-body scope issues
        _check_id = id
        _category = category
        _timeout = timeout
        _can_parallel = can_parallel

        # Dynamically create a Check subclass
        class FuncCheck(Check):
            check_id = _check_id
            category = _category
            title = _title
            description = _description
            # Expose meta attributes for executor
            timeout = _timeout
            depends_on = _depends_on
            tags = _tags
            can_parallel = _can_parallel

            def run(self) -> CheckResult:
                return fn(ctx)

        # Preserve function identity for debugging
        FuncCheck.__name__ = _class_name
        FuncCheck.__qualname__ = _class_name
        FuncCheck.__doc__ = fn.__doc__
        FuncCheck.__module__ = fn.__module__
        FuncCheck._check_fn = fn
        FuncCheck._check_ctx = ctx

        # Auto-register
        from .registry import register_check
        register_check(FuncCheck)

        return FuncCheck

    return decorator
