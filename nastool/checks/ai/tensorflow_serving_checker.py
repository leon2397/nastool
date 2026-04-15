# -*- coding: utf-8 -*-
"""TensorFlow Serving 检测"""

import subprocess
import requests
import shutil

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class TensorFlowServingCheck(Check):
    """检测 TensorFlow Serving 推理服务状态"""

    check_id = "tensorflow_serving"
    category = CheckCategory.AI
    title = "TensorFlow Serving"
    description = "检查 TensorFlow Serving 推理服务状态"

    def __init__(self, host: str = "localhost", port: int = 8501):
        super().__init__()
        self.host = host
        self.port = port

    def run(self) -> CheckResult:
        # 通过 REST API 检测
        try:
            resp = requests.get(f"http://{self.host}:{self.port}/v1/models", timeout=5)
            if resp.status_code == 200:
                try:
                    models = resp.json().get("model_version_status", []) or resp.json().get("models", [])
                except Exception:
                    models = []
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="running",
                    expected="running",
                    message=f"TensorFlow Serving 运行中 (models: {len(models)})",
                    fix_available=False,
                    details={"model_count": len(models)},
                )
        except requests.exceptions.RequestException:
            pass

        # 通过进程检测
        try:
            result = subprocess.run(
                ["pgrep", "-f", "tensorflow_model_server"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return CheckResult(
                    check_id=self.check_id, category=self.category,
                    severity=CheckSeverity.PASSED, passed=True,
                    title=self.title, current="running",
                    expected="running",
                    message="TensorFlow Serving 进程运行中",
                    fix_available=False,
                )
        except Exception:
            pass

        # 检查命令
        tfs = shutil.which("tensorflow_model_server")
        if tfs:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.WARNING, passed=False,
                title=self.title, current="installed",
                expected="running",
                message="TensorFlow Serving 已安装但未运行",
                fix_available=True,
                fix_id="start_tf_serving",
                fix_command="tensorflow_model_server --port=8500 --model_name=my_model",
                fix_description="启动 TensorFlow Serving",
                fix_risk="low",
            )

        return CheckResult(
            check_id=self.check_id, category=self.category,
            severity=CheckSeverity.WARNING, passed=False,
            title=self.title, current="not installed",
            expected="running",
            message="TensorFlow Serving 未安装",
            fix_available=True,
            fix_id="install_tf_serving",
            fix_command="docker pull tensorflow/serving",
            fix_description="安装 TensorFlow Serving",
            fix_risk="medium",
        )
