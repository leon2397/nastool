# -*- coding: utf-8 -*-
"""TorchServe 检测 (declarative style)"""

from __future__ import annotations

import os
import subprocess
import shutil

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult

_TSERVE_HOST = "localhost"
_TSERVE_PORT = 8080


@check(
    id="torchserve",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="TorchServe",
    description="检查 PyTorch TorchServe 推理服务状态",
    timeout=15,
    enable_accuracy=True)
def torchserve(ctx: CheckContext) -> CheckResult:
    """检测 PyTorch TorchServe 推理服务状态"""
    try:
        import requests
    except ImportError:
        requests = None

    # 通过 HTTP API 检测
    if requests:
        try:
            resp = requests.get(f"http://{_TSERVE_HOST}:{_TSERVE_PORT}/v1/models", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return ctx.passed(
                    current="running", expected="running",
                    message=f"TorchServe 运行中 (models: {len(models)})",
                    details={"model_count": len(models)},
                )
        except Exception:
            pass

    # 通过进程检测
    try:
        result = subprocess.run(["pgrep", "-f", "torchserve"], capture_output=True, text=True, errors="replace", timeout=5)
        if result.returncode == 0:
            return ctx.passed(current="running", expected="running", message="TorchServe 进程运行中")
    except Exception:
        pass

    # 检查命令
    if shutil.which("torchserve"):
        return ctx.failed(
            current="installed", expected="running",
            message="TorchServe 已安装但未运行",
            fix_available=True, fix_id="start_torchserve",
            fix_command="torchserve --start --model-store /model_store",
            fix_description="启动 TorchServe", fix_risk="low",
        )

    # 检查 .mar 文件
    for store in ["/model_store", "/opt/model_store"]:
        if os.path.exists(store):
            mar_files = [f for f in os.listdir(store) if f.endswith(".mar")]
            if mar_files:
                return ctx.failed(
                    current=f"{len(mar_files)} .mar files", expected="running",
                    message=f"找到 {len(mar_files)} 个 TorchServe 模型存档",
                    fix_available=True, fix_id="start_torchserve",
                    fix_command="torchserve --start --model-store /model_store",
                    fix_description="启动 TorchServe", fix_risk="low",
                )

    return ctx.failed(
        current="not installed", expected="running",
        message="TorchServe 未安装",
        fix_available=True, fix_id="install_torchserve",
        fix_command="pip install torchserve",
        fix_description="安装 TorchServe", fix_risk="medium",
    )


# Backward-compatible class alias
TorchServeCheck = torchserve
