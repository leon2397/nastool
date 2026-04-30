# -*- coding: utf-8 -*-
"""PaddlePaddle 版本检测 (declarative style)"""

from __future__ import annotations

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult


@check(
    id="paddlepaddle_version",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="PaddlePaddle Version",
    description="检查百度 PaddlePaddle 深度学习框架版本",
    timeout=10,
    enable_accuracy=True)
def paddlepaddle_version(ctx: CheckContext) -> CheckResult:
    """检测 PaddlePaddle (飞桨) 是否安装及版本"""
    try:
        import paddle
        version = paddle.__version__
        try:
            gpu_info = ""
            if paddle.is_compiled_with_cuda():
                gpu_info = f", CUDA {paddle.version.cuda()}, cuDNN {paddle.version.cudnn()}"
            message = f"PaddlePaddle {version} ({gpu_info.strip(', ')})"
        except Exception:
            message = f"PaddlePaddle {version} (CPU)"
        return ctx.passed(
            current=version,
            expected="installed",
            message=message,
        )
    except ImportError:
        return ctx.failed(
            current="not installed",
            expected="installed",
            message="PaddlePaddle 未安装",
            fix_available=True,
            fix_id="install_paddle",
            fix_command="pip install paddlepaddle",
            fix_description="安装百度 PaddlePaddle",
            fix_risk="low",
        )


# Backward-compatible class alias
PaddlePaddleCheck = paddlepaddle_version
