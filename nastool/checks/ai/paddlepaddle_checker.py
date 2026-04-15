# -*- coding: utf-8 -*-
"""PaddlePaddle 版本检测"""

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class PaddlePaddleCheck(Check):
    """检测 PaddlePaddle (飞桨) 是否安装及版本"""

    check_id = "paddlepaddle_version"
    category = CheckCategory.AI
    title = "PaddlePaddle Version"
    description = "检查百度 PaddlePaddle 深度学习框架版本"

    def run(self) -> CheckResult:
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
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.PASSED, passed=True,
                title=self.title, current=version,
                expected="installed",
                message=message,
                fix_available=False,
            )
        except ImportError:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.WARNING, passed=False,
                title=self.title, current="not installed",
                expected="installed",
                message="PaddlePaddle 未安装",
                fix_available=True,
                fix_id="install_paddle",
                fix_command="pip install paddlepaddle",
                fix_description="安装百度 PaddlePaddle",
                fix_risk="low",
            )
