# -*- coding: utf-8 -*-
"""TensorFlow Serving 检测 (declarative style)"""

from __future__ import annotations

import subprocess
import shutil

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult

_TFS_HOST = "localhost"
_TFS_PORT = 8501


@check(
    id="tensorflow_serving",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="TensorFlow Serving",
    description="检查 TensorFlow Serving 推理服务状态",
    timeout=15,
)
def tensorflow_serving(ctx: CheckContext) -> CheckResult:
    """检测 TensorFlow Serving 推理服务状态"""
    try:
        import requests
    except ImportError:
        requests = None

    # 通过 REST API 检测
    if requests:
        try:
            resp = requests.get(f"http://{_TFS_HOST}:{_TFS_PORT}/v1/models", timeout=5)
            if resp.status_code == 200:
                try:
                    models = resp.json().get("model_version_status", []) or resp.json().get("models", [])
                except Exception:
                    models = []
                return ctx.passed(
                    current="running", expected="running",
                    message=f"TensorFlow Serving 运行中 (models: {len(models)})",
                    details={"model_count": len(models)},
                )
        except Exception:
            pass

    # 通过进程检测
    try:
        result = subprocess.run(
            ["pgrep", "-f", "tensorflow_model_server"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return ctx.passed(current="running", expected="running", message="TensorFlow Serving 进程运行中")
    except Exception:
        pass

    # 检查命令
    if shutil.which("tensorflow_model_server"):
        return ctx.failed(
            current="installed", expected="running",
            message="TensorFlow Serving 已安装但未运行",
            fix_available=True, fix_id="start_tf_serving",
            fix_command="tensorflow_model_server --port=8500 --model_name=my_model",
            fix_description="启动 TensorFlow Serving", fix_risk="low",
        )

    return ctx.failed(
        current="not installed", expected="running",
        message="TensorFlow Serving 未安装",
        fix_available=True, fix_id="install_tf_serving",
        fix_command="docker pull tensorflow/serving",
        fix_description="安装 TensorFlow Serving", fix_risk="medium",
    )


# Backward-compatible class alias
TensorFlowServingCheck = tensorflow_serving
