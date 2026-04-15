# -*- coding: utf-8 -*-
"""模型格式检测"""

from pathlib import Path

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class ModelFormatCheck(Check):
    """检测常见 AI 模型格式文件"""

    check_id = "model_format"
    category = CheckCategory.AI
    title = "Model Format"
    description = "检查常见 AI 模型格式文件 (.onnx/.pt/.h5/.pb)"

    # 支持的模型格式
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

    DEFAULT_PATHS = [
        "/models", "/opt/models", "/root/models",
        "/home/models", "C:\\models",
        "./models", "./checkpoints", "./outputs",
    ]

    def __init__(self, model_paths: list = None):
        super().__init__()
        self.model_paths = model_paths or self.DEFAULT_PATHS

    def run(self) -> CheckResult:
        found = {}
        for search_path in self.model_paths:
            path = Path(search_path)
            if not path.exists():
                continue
            try:
                for ext, desc in self.MODEL_FORMATS.items():
                    for model_file in path.rglob(f"*{ext}"):
                        size_mb = model_file.stat().st_size / (1024 * 1024)
                        key = f"{desc} ({ext})"
                        if key not in found:
                            found[key] = 0
                        found[key] += 1
            except Exception:
                pass

        if found:
            parts = [f"{k}: {v} 个" for k, v in found.items()]
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.PASSED, passed=True,
                title=self.title, current=f"{sum(found.values())} models",
                expected="models available",
                message="; ".join(parts),
                fix_available=False,
                details={"formats": found},
            )
        else:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.WARNING, passed=False,
                title=self.title, current="no models found",
                expected="models available",
                message="未找到任何 AI 模型文件",
                fix_available=True,
                fix_id="download_models",
                fix_description="下载 AI 模型文件",
                fix_risk="low",
            )
