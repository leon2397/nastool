# -*- coding: utf-8 -*-
"""模型格式检测 (declarative style)"""

from __future__ import annotations

from pathlib import Path

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult

MODEL_FORMATS = {
    ".onnx": "ONNX",
    ".pt": "PyTorch",
    ".pth": "PyTorch StateDict",
    ".h5": "Keras/HDF5",
    ".pb": "TensorFlow ProtoBuf",
    ".tflite": "TensorFlow Lite",
    ".mlmodel": "Core ML",
    ".caffemodel": "Caffe",
    ".paddle": "PaddlePaddle",
}

DEFAULT_MODEL_PATHS = [
    "/models", "/opt/models", "/root/models",
    "/home/models", "C:\\models",
    "./models", "./checkpoints", "./outputs",
]


@check(
    id="model_format",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="Model Format",
    description="检查常见 AI 模型格式文件 (.onnx/.pt/.h5/.pb)",
    timeout=15,
)
def model_format(ctx: CheckContext) -> CheckResult:
    """检测常见 AI 模型格式文件"""
    found = {}
    for search_path in DEFAULT_MODEL_PATHS:
        path = Path(search_path)
        if not path.exists():
            continue
        try:
            for ext, desc in MODEL_FORMATS.items():
                for model_file in path.rglob(f"*{ext}"):
                    try:
                        size_mb = model_file.stat().st_size / (1024 * 1024)
                    except (PermissionError, OSError):
                        size_mb = 0
                    key = f"{desc} ({ext})"
                    if key not in found:
                        found[key] = 0
                    found[key] += 1
        except Exception:
            pass

    if found:
        parts = [f"{k}: {v} 个" for k, v in found.items()]
        return ctx.passed(
            current=f"{sum(found.values())} models",
            expected="models available",
            message="; ".join(parts),
            details={"formats": found},
        )

    return ctx.failed(
        current="no models found",
        expected="models available",
        message="未找到任何 AI 模型文件",
        fix_available=True,
        fix_id="download_models",
        fix_description="下载 AI 模型文件",
        fix_risk="low",
    )


# Backward-compatible class alias
ModelFormatCheck = model_format
