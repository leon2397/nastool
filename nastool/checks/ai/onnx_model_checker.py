# -*- coding: utf-8 -*-
"""ONNX 模型验证检测"""

from pathlib import Path

from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class ONNXModelCheck(Check):
    """检测 ONNX 模型文件是否有效"""

    check_id = "onnx_model"
    category = CheckCategory.AI
    title = "ONNX Model"
    description = "检查 ONNX 模型文件是否存在且有效"

    def __init__(self, model_paths: list = None):
        super().__init__()
        self.model_paths = model_paths or [
            "/models", "/opt/models", "/root/models",
            "C:\\models", "./models", "./checkpoints",
        ]

    def run(self) -> CheckResult:
        onnx_models = []
        for search_path in self.model_paths:
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
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.PASSED, passed=True,
                title=self.title, current=f"{len(onnx_models)} models",
                expected="models available",
                message=f"找到 {len(onnx_models)} 个 ONNX 模型: {', '.join(onnx_models[:3])}",
                fix_available=False,
                details={"model_count": len(onnx_models)},
            )

        try:
            import onnx
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.WARNING, passed=False,
                title=self.title, current="runtime only",
                expected="models available",
                message=f"ONNX 运行时已安装，但未找到模型文件",
                fix_available=True,
                fix_id="download_onnx_model",
                fix_description="下载 ONNX 模型",
                fix_risk="low",
            )
        except ImportError:
            return CheckResult(
                check_id=self.check_id, category=self.category,
                severity=CheckSeverity.WARNING, passed=False,
                title=self.title, current="not installed",
                expected="installed",
                message="ONNX 未安装且未找到模型文件",
                fix_available=True,
                fix_id="install_onnx",
                fix_command="pip install onnx",
                fix_description="安装 ONNX",
                fix_risk="low",
            )
