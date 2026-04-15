# -*- coding: utf-8 -*-
"""Keras 版本检测 (declarative style)"""

from __future__ import annotations

from checks.decorators import check, CheckContext
from checks.base import CheckCategory, CheckSeverity, CheckResult


@check(
    id="keras_version",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="Keras Version",
    description="检查 Keras 深度学习框架版本",
    timeout=10,
)
def keras_version(ctx: CheckContext) -> CheckResult:
    """检测 Keras 是否安装及版本"""
    try:
        import keras
        version = keras.__version__
        try:
            backend = keras.backend.backend()
        except Exception:
            backend = "unknown"
        return ctx.passed(
            current=version,
            expected="installed",
            message=f"Keras {version} (backend: {backend})",
            details={"version": version, "backend": backend},
        )
    except ImportError:
        return ctx.failed(
            current="not installed",
            expected="installed",
            message="Keras 未安装",
            fix_available=True,
            fix_id="install_keras",
            fix_command="pip install keras",
            fix_description="安装 Keras",
            fix_risk="low",
        )


# Backward-compatible class alias
KerasVersionCheck = keras_version
