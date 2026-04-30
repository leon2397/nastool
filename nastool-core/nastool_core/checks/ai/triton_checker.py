# -*- coding: utf-8 -*-
"""Triton Inference Server 检测 (declarative style)"""

from __future__ import annotations

import subprocess
import shutil

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult

_TRITON_HOST = "localhost"
_TRITON_PORT = 8000


@check(
    id="triton_server",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="Triton Server",
    description="检查 Triton Inference Server 是否运行",
    timeout=15,
    enable_accuracy=True)
def triton_server(ctx: CheckContext) -> CheckResult:
    """检测 NVIDIA Triton Inference Server 状态"""
    try:
        import requests
    except ImportError:
        # Fallback: check process only
        try:
            result = subprocess.run(["pgrep", "-f", "tritonserver"], capture_output=True, text=True, errors="replace", timeout=5)
            if result.returncode == 0:
                return ctx.passed(current="running", expected="running", message="Triton Server 进程运行中")
        except Exception:
            pass
        return ctx.failed(
            current="not installed",
            expected="running",
            message="Triton Server 未安装 (requests 库不可用)",
            fix_available=True,
            fix_id="install_triton",
            fix_command="docker pull nvcr.io/nvidia/tritonserver:xx.x-py3",
            fix_description="安装 Triton Inference Server",
            fix_risk="medium",
        )

    # 通过 HTTP API 检测
    try:
        resp = requests.get(f"http://{_TRITON_HOST}:{_TRITON_PORT}/v2/health", timeout=5)
        if resp.status_code == 200:
            try:
                meta_resp = requests.get(f"http://{_TRITON_HOST}:{_TRITON_PORT}/v2/models", timeout=5)
                if meta_resp.status_code == 200:
                    models = meta_resp.json().get("models", [])
                    return ctx.passed(
                        current="running", expected="running",
                        message=f"Triton Server 运行中 (models: {len(models)})",
                        details={"model_count": len(models)},
                    )
            except Exception:
                pass
            return ctx.passed(current="running", expected="running", message="Triton Server 运行中")
    except Exception:
        pass

    # 通过进程检测
    try:
        result = subprocess.run(["pgrep", "-f", "tritonserver"], capture_output=True, text=True, errors="replace", timeout=5)
        if result.returncode == 0:
            return ctx.passed(current="running", expected="running", message="Triton Server 进程运行中")
    except Exception:
        pass

    # 检查命令
    if shutil.which("tritonserver"):
        return ctx.failed(
            current="installed", expected="running",
            message="Triton Server 已安装但未运行",
            fix_available=True, fix_id="start_triton",
            fix_command="tritonserver --model-repository=/models",
            fix_description="启动 Triton Server", fix_risk="low",
        )

    return ctx.failed(
        current="not installed", expected="running",
        message="Triton Server 未安装",
        fix_available=True, fix_id="install_triton",
        fix_command="docker pull nvcr.io/nvidia/tritonserver:xx.x-py3",
        fix_description="安装 Triton Inference Server", fix_risk="medium",
    )


# Backward-compatible class alias
TritonServerCheck = triton_server
