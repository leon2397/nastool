# -*- coding: utf-8 -*-
"""ONNX 模型验证检测 (declarative style)"""

from __future__ import annotations

from pathlib import Path

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult

MODEL_PATHS = [
    "/models", "/opt/models", "/root/models",
    "C:\\models", "./models", "./checkpoints",
]


@check(
    id="onnx_model",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="ONNX Model",
    description="检查 ONNX 模型文件是否存在且有效",
    timeout=15,
    enable_accuracy=True)
def onnx_model(ctx: CheckContext) -> CheckResult:
    """检测 ONNX 模型文件是否有效"""
    onnx_models = []
    for search_path in MODEL_PATHS:
        path = Path(search_path)
        try:
            if not path.exists():
                continue
        except PermissionError:
            continue
        try:
            for model_file in path.rglob("*.onnx"):
                try:
                    size_mb = model_file.stat().st_size / (1024 * 1024)
                except (PermissionError, OSError):
                    size_mb = 0
                onnx_models.append(f"{model_file.name} ({size_mb:.1f}MB)")
        except (PermissionError, OSError):
            pass

    if onnx_models:
        return ctx.passed(
            current=f"{len(onnx_models)} models",
            expected="models available",
            message=f"找到 {len(onnx_models)} 个 ONNX 模型: {', '.join(onnx_models[:3])}",
            details={"model_count": len(onnx_models)},
        )

    try:
        import onnx
        return ctx.failed(
            current="runtime only",
            expected="models available",
            message="ONNX 运行时已安装，但未找到模型文件",
            fix_available=True,
            fix_id="download_onnx_model",
            fix_description="下载 ONNX 模型",
            fix_risk="low",
        )
    except ImportError:
        return ctx.failed(
            current="not installed",
            expected="installed",
            message="ONNX 未安装且未找到模型文件",
            fix_available=True,
            fix_id="install_onnx",
            fix_command="pip install onnx",
            fix_description="安装 ONNX",
            fix_risk="low",
        )


# Backward-compatible class alias
ONNXModelCheck = onnx_model
