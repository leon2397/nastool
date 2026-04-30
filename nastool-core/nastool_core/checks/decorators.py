# -*- coding: utf-8 -*-
"""
checks/decorators.py - Declarative check definition via @check() decorator with accuracy enhancement

Usage (new style -- function-based):
    from checks.decorators import check, CheckContext

    @check(
        id="tensorflow_version",
        category=CheckCategory.AI,
        severity=CheckSeverity.WARNING,
        timeout=10,
        depends_on=["gpu_detected"],
        enable_accuracy=True,  # 启用准确性保障
    )
    def tensorflow_version(ctx: CheckContext) -> CheckResult:
        '''Check TensorFlow version'''
        # 使用多源数据采集
        sources = []
        
        # 数据源1: 直接导入
        try:
            import tensorflow as tf
            sources.append(ctx.create_source_result(tf.__version__, "import", confidence=0.95))
        except:
            pass
        
        # 数据源2: 命令行检查
        version = ctx.run_command("python -c 'import tensorflow as tf; print(tf.__version__)'")
        if version:
            sources.append(ctx.create_source_result(version, "command", confidence=0.9))
        
        return ctx.result(
            passed=True,
            current=version,
            expected="latest",
            message=f"TensorFlow {version}",
            data_sources=sources,  # 传入数据源进行融合
        )

Old style (class-based) still works -- no breaking changes.
"""

from __future__ import annotations

import functools
from typing import Callable, List, Optional, Any, Tuple, Dict

from .base import Check, CheckResult, CheckCategory, CheckSeverity


# Map string category names to CheckCategory enum (case-insensitive)
_STRING_TO_CATEGORY = {c.value.upper(): c for c in CheckCategory}


def _normalize_category(cat) -> CheckCategory:
    """Accept CheckCategory enum or string (case-insensitive)."""
    if isinstance(cat, CheckCategory):
        return cat
    if isinstance(cat, str):
        upper = cat.upper()
        if upper in _STRING_TO_CATEGORY:
            return _STRING_TO_CATEGORY[upper]
        # Try exact match
        for c in CheckCategory:
            if c.value == cat:
                return c
    raise ValueError(f"Invalid category: {cat!r}. Must be CheckCategory enum or string.")


class CheckContext:
    """
    Helper context passed to function-based checks.
    Provides convenience methods for common operations.
    Enhanced with accuracy features.
    """

    __slots__ = ("check_id", "category", "severity", "title", "description",
                 "timeout", "depends_on", "tags", "can_parallel",
                 "_enable_accuracy", "_data_sources")

    def __init__(
        self,
        check_id: str,
        category,  # CheckCategory or str
        severity: CheckSeverity,
        title: str,
        description: str = "",
        timeout: float = 30.0,
        depends_on: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        can_parallel: bool = True,
        enable_accuracy: bool = True,
    ):
        self.check_id = check_id
        self.category = _normalize_category(category)
        self.severity = severity
        self.title = title
        self.description = description
        self.timeout = timeout
        self.depends_on = depends_on or []
        self.tags = tags or []
        self.can_parallel = can_parallel
        self._enable_accuracy = enable_accuracy
        self._data_sources = []  # 存储数据源结果

    # ── Accuracy enhancement methods ──────────────────────────────────

    def create_source_result(self, value: Any, source: str, confidence: float = 1.0):
        """
        Create a data source result for accuracy enhancement.
        
        Args:
            value: The value from this data source
            source: Name/identifier of the data source
            confidence: Confidence level (0.0-1.0) of this source
            
        Returns:
            A DataSourceResult-like dictionary
        """
        from datetime import datetime
        return {
            "value": value,
            "source": source,
            "timestamp": datetime.now().timestamp(),
            "confidence": confidence
        }

    def add_data_source(self, value: Any, source: str, confidence: float = 1.0):
        """
        Add a data source result to the collection.
        
        Args:
            value: The value from this data source
            source: Name/identifier of the data source
            confidence: Confidence level (0.0-1.0) of this source
        """
        self._data_sources.append(self.create_source_result(value, source, confidence))

    def get_data_sources(self) -> List[dict]:
        """Get all collected data sources."""
        return self._data_sources

    def clear_data_sources(self):
        """Clear all collected data sources."""
        self._data_sources = []

    # ── Result builders ──────────────────────────────────────────────

    def passed(
        self,
        current: str = "",
        expected: str = "",
        message: str = "",
        severity: Optional[CheckSeverity] = None,
        details: Optional[dict] = None,
        data_sources: Optional[List[dict]] = None,
        confidence: float = 1.0,
        **kwargs,
    ) -> CheckResult:
        """Build a passing CheckResult with accuracy support."""
        result = CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity or CheckSeverity.PASSED,
            passed=True,
            title=self.title,
            current=current,
            expected=expected,
            message=message,
            details=details or {},
            confidence=confidence,
            **kwargs,
        )
        
        # Apply accuracy enhancement if enabled
        if self._enable_accuracy and (data_sources or self._data_sources):
            sources = data_sources or self._data_sources
            result.data_sources = [s["source"] for s in sources]
            result.confidence = self._calculate_confidence(sources)
        
        return result

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
        data_sources: Optional[List[dict]] = None,
        confidence: float = 1.0,
        **kwargs,
    ) -> CheckResult:
        """Build a failing CheckResult with accuracy support."""
        result = CheckResult(
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
            confidence=confidence,
            **kwargs,
        )
        
        # Apply accuracy enhancement if enabled
        if self._enable_accuracy and (data_sources or self._data_sources):
            sources = data_sources or self._data_sources
            result.data_sources = [s["source"] for s in sources]
            result.confidence = self._calculate_confidence(sources)
        
        return result

    def warning(
        self,
        current: str = "",
        expected: str = "",
        message: str = "",
        details: Optional[dict] = None,
        data_sources: Optional[List[dict]] = None,
        confidence: float = 1.0,
        **kwargs,
    ) -> CheckResult:
        """Build a warning (passed=True but attention needed) with accuracy support."""
        result = CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=CheckSeverity.WARNING,
            passed=True,
            title=self.title,
            current=current,
            expected=expected,
            message=message,
            details=details or {},
            confidence=confidence,
            **kwargs,
        )
        
        # Apply accuracy enhancement if enabled
        if self._enable_accuracy and (data_sources or self._data_sources):
            sources = data_sources or self._data_sources
            result.data_sources = [s["source"] for s in sources]
            result.confidence = self._calculate_confidence(sources)
        
        return result

    def info(
        self,
        current: str = "",
        expected: str = "",
        message: str = "",
        details: Optional[dict] = None,
        data_sources: Optional[List[dict]] = None,
        confidence: float = 1.0,
        **kwargs,
    ) -> CheckResult:
        """Build an informational CheckResult with accuracy support."""
        result = CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=CheckSeverity.INFO,
            passed=True,
            title=self.title,
            current=current,
            expected=expected,
            message=message,
            details=details or {},
            confidence=confidence,
            **kwargs,
        )
        
        # Apply accuracy enhancement if enabled
        if self._enable_accuracy and (data_sources or self._data_sources):
            sources = data_sources or self._data_sources
            result.data_sources = [s["source"] for s in sources]
            result.confidence = self._calculate_confidence(sources)
        
        return result

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
            confidence=0.0,
        )

    def result(
        self,
        passed: bool,
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
        data_sources: Optional[List[dict]] = None,
        confidence: float = 1.0,
        **kwargs,
    ) -> CheckResult:
        """Build a CheckResult based on passed status with accuracy support.

        This is a convenience method that delegates to passed() or failed()
        based on the passed parameter. Useful for dynamic result building.
        """
        if passed:
            return self.passed(
                current=current,
                expected=expected,
                message=message,
                severity=severity,
                details=details,
                data_sources=data_sources,
                confidence=confidence,
                **kwargs,
            )
        else:
            return self.failed(
                current=current,
                expected=expected,
                message=message,
                severity=severity,
                fix_available=fix_available,
                fix_id=fix_id,
                fix_command=fix_command,
                fix_description=fix_description,
                fix_risk=fix_risk,
                details=details,
                data_sources=data_sources,
                confidence=confidence,
                **kwargs,
            )

    def _calculate_confidence(self, sources: List[dict]) -> float:
        """
        Calculate overall confidence based on multiple data sources.
        
        Args:
            sources: List of data source dictionaries with 'confidence' key
            
        Returns:
            Overall confidence score (0.0-1.0)
        """
        if not sources:
            return 1.0
        
        # 基础置信度：源数量得分 (最多5个源)
        source_count = len(sources)
        source_confidence = min(source_count / 5.0, 1.0)
        
        # 源权重得分：平均置信度
        total_confidence = sum(s.get("confidence", 1.0) for s in sources)
        source_weights = total_confidence / source_count
        
        # 计算一致性得分
        values = [s["value"] for s in sources if s["value"] is not None]
        if len(values) >= 2:
            try:
                # 数值一致性检查
                numeric_values = [float(v) for v in values if isinstance(v, (int, float, str)) 
                                and str(v).replace('.', '', 1).isdigit()]
                if numeric_values:
                    mean_val = sum(numeric_values) / len(numeric_values)
                    variance = sum((v - mean_val) ** 2 for v in numeric_values) / len(numeric_values)
                    std_dev = variance ** 0.5
                    # 一致性 = 1 - 变异系数 (标准化后的标准差)
                    if mean_val != 0:
                        cv = std_dev / abs(mean_val)
                        consistency = max(0.0, min(1.0, 1 - cv))
                    else:
                        consistency = 1.0
                else:
                    # 非数值数据，比较相等性
                    unique_values = len(set(values))
                    consistency = max(0.3, 1.0 - (unique_values - 1) / len(values))
            except:
                consistency = 0.7
        else:
            consistency = 1.0
        
        # 综合置信度 = 源数量(40%) + 源权重(30%) + 一致性(30%)
        overall = (source_confidence * 0.4) + (source_weights * 0.3) + (consistency * 0.3)
        return round(max(0.0, min(1.0, overall)), 2)

    # ── System helpers (delegate to Check base methods) ──────────────

    def run_command(self, cmd: str, timeout: int = 10) -> str:
        """Run a shell command and return stdout."""
        import subprocess
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, errors="replace", timeout=timeout
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def read_file(self, path: str) -> str:
        """Read file contents."""
        try:
            with open(path, "r", encoding="utf-8") as f:
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
    category,  # CheckCategory or str (string auto-normalized)
    severity: CheckSeverity = CheckSeverity.WARNING,
    title: Optional[str] = None,
    description: str = "",
    timeout: float = 30.0,
    depends_on: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    can_parallel: bool = True,
    class_name: Optional[str] = None,
    enable_accuracy: bool = True,  # 新增：是否启用准确性保障
):
    """
    Decorator to declare a function-based check with accuracy enhancement.

    Wraps a plain function into a Check subclass that is auto-registered
    in the check registry.  The function receives a CheckContext and must
    return a CheckResult.

    Args:
        id: Unique identifier for the check
        category: Check category (CheckCategory enum or string)
        severity: Default severity for failures
        title: Human-readable title (auto-generated from function name if not provided)
        description: Detailed description
        timeout: Maximum execution time in seconds
        depends_on: List of check IDs this check depends on
        tags: Tags for categorization
        can_parallel: Whether this check can run in parallel
        class_name: Custom class name for the generated Check subclass
        enable_accuracy: Enable accuracy enhancement features

    Example:
        @check(id="gpu_detected", category=CheckCategory.AI)
        def gpu_detected(ctx: CheckContext) -> CheckResult:
            # Collect multiple data sources
            sources = []
            if ctx.file_exists("/dev/nvidia0"):
                sources.append(ctx.create_source_result("nvidia", "device_file", confidence=0.9))
            if ctx.command_exists("nvidia-smi"):
                sources.append(ctx.create_source_result("nvidia-smi", "command", confidence=0.95))
            return ctx.passed(
                current="detected" if sources else "none",
                message="GPU found" if sources else "No GPU detected",
                data_sources=sources,
            )
    """

    def decorator(fn: Callable[[CheckContext], CheckResult]) -> type:
        # Build a human-friendly title from function name if not provided
        _title = title or fn.__name__.replace("_", " ").title()
        _description = description or fn.__doc__ or _title
        _depends_on = depends_on or []
        _tags = tags or []
        _class_name = class_name or _id_to_class_name(id)

        # Create CheckContext instance (shared metadata) with accuracy support
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
            enable_accuracy=enable_accuracy,
        )

        # Capture closure values to avoid class-body scope issues
        _check_id = id
        _category = _normalize_category(category)
        _timeout = timeout
        _can_parallel = can_parallel
        _enable_accuracy = enable_accuracy

        # Dynamically create a Check subclass with accuracy enhancement
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
            # Accuracy enhancement configuration
            enable_data_fusion = _enable_accuracy
            enable_consistency_check = _enable_accuracy

            def run(self) -> CheckResult:
                # Execute the check function
                result = fn(ctx)
                
                # If accuracy is enabled and result doesn't have confidence set,
                # calculate it based on collected data sources
                if _enable_accuracy and result.confidence == 1.0 and ctx._data_sources:
                    result.confidence = ctx._calculate_confidence(ctx._data_sources)
                    result.data_sources = [s["source"] for s in ctx._data_sources]
                
                return result

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
