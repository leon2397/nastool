# -*- coding: utf-8 -*-
"""
nastool adapters - 设备适配层

提供昇腾和 Jetson 两大设备族的自动识别与检测。
"""

from adapters.base import BaseAdapter, AdapterResult
from adapters.detector import detect, detect_with_manual

__all__ = [
    "BaseAdapter",
    "AdapterResult",
    "detect",
    "detect_with_manual",
]
