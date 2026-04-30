# -*- coding: utf-8 -*-
"""TensorFlow 版本检测 (declarative style)"""

from __future__ import annotations

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult


@check(
    id="tensorflow_version",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="TensorFlow Version",
    description="检查 TensorFlow 深度学习框架版本",
    timeout=10,
)
def tensorflow_version(ctx: CheckContext) -> CheckResult:
    """检测 TensorFlow 是否安装及版本"""
    try:
        import tensorflow as tf

        version = tf.__version__
        gpus = tf.config.list_physical_devices("GPU")
        if gpus:
            return ctx.passed(
                current=version,
                expected="latest",
                message=f"TensorFlow {version} (GPU: {len(gpus)} device(s))",
                details={"version": version, "gpu_count": len(gpus)},
            )
        return ctx.warning(
            current=version,
            expected="latest",
            message=f"TensorFlow {version} (无 GPU 支持)",
            details={"version": version, "gpu_count": 0},
        )
    except ImportError:
        return ctx.failed(
            current="not installed",
            expected="installed",
            message="TensorFlow 未安装",
            fix_available=True,
            fix_id="install_tensorflow",
            fix_command="pip install tensorflow",
            fix_description="安装 TensorFlow CPU 版本",
            fix_risk="low",
        )


# Backward-compatible class alias
TensorFlowVersionCheck = tensorflow_version
