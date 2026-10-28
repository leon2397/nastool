"""
core/__init__.py — 核心引擎统一导出
"""
from .device import get_device_info
from .network import check_network
from .platform_detect import detect_platform
from .runner import DiagnosticResult, RunOptions, run_diagnostics
from .scoring import compute_score
from .services import detect_services
from .ai_accel import detect_ai_accelerator
from .storage import check_storage

__all__ = [
    "get_device_info",
    "check_storage",
    "check_network",
    "detect_services",
    "detect_platform",
    "detect_ai_accelerator",
    "compute_score",
    "run_diagnostics",
    "RunOptions",
    "DiagnosticResult",
]
