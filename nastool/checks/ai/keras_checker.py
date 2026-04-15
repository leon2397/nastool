# -*- coding: utf-8 -*-
"""Keras 版本检测"""

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class KerasVersionCheck(Check):
    """检测 Keras 是否安装及版本"""

    check_id = "keras_version"
    category = CheckCategory.AI
    title = "Keras Version"
    description = "检查 Keras 深度学习框架版本"

    def run(self) -> CheckResult:
        """执行检测"""
        try:
            import keras
            version = keras.__version__
            try:
                backend = keras.backend.backend()
            except Exception:
                backend = "unknown"
            severity = CheckSeverity.PASSED
            passed = True
            message = f"Keras {version} (backend: {backend})"
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=severity,
                passed=passed,
                title=self.title,
                current=version,
                expected="installed",
                message=message,
                fix_available=False,
                details={"version": version, "backend": backend},
            )
        except ImportError:
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.WARNING,
                passed=False,
                title=self.title,
                current="not installed",
                expected="installed",
                message="Keras 未安装",
                fix_available=True,
                fix_id="install_keras",
                fix_command="pip install keras",
                fix_description="安装 Keras",
                fix_risk="low",
            )
