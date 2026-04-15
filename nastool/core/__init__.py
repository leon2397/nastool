"""
core/__init__.py — 核心引擎统一导出
"""

from .device import get_device_info
from .storage import check_storage
from .network import check_network
from .ai_accel import detect_ai_accelerator

__all__ = [
    "get_device_info",
    "check_storage",
    "check_network",
    "detect_ai_accelerator",
]
