# -*- coding: utf-8 -*-
"""TensorFlow 版本检测"""

import shutil

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class TensorFlowVersionCheck(Check):
    """检测 TensorFlow 是否安装及版本"""

    check_id = "tensorflow_version"
    category = CheckCategory.AI
    title = "TensorFlow Version"
    description = "检查 TensorFlow 深度学习框架版本"

    def run(self) -> CheckResult:
        """执行检测"""
        # 检查 tensorflow-gpu 命令
        tensorflow_cli = shutil.which("tensorflow") or shutil.which("tensorflow-gpu")

        # 尝试导入 tensorflow
        try:
            import tensorflow as tf

            version = tf.__version__
            # 检查是否有 GPU 支持
            gpus = tf.config.list_physical_devices("GPU")
            if gpus:
                severity = CheckSeverity.PASSED
                passed = True
                message = f"TensorFlow {version} (GPU: {len(gpus)} device(s))"
            else:
                severity = CheckSeverity.WARNING
                passed = True
                message = f"TensorFlow {version} (无 GPU 支持)"

            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=severity,
                passed=passed,
                title=self.title,
                current=version,
                expected="latest",
                message=message,
                fix_available=False,
                details={"version": version, "gpu_count": len(gpus)},
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
                message="TensorFlow 未安装",
                fix_available=True,
                fix_id="install_tensorflow",
                fix_command="pip install tensorflow",
                fix_description="安装 TensorFlow CPU 版本",
                fix_risk="low",
            )
