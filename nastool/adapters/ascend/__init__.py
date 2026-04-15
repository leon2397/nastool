# -*- coding: utf-8 -*-
"""
nastool adapters.ascend - 昇腾适配器模块

模块：
- common: 通用适配器（4类设备检测）
- npu: NPU 详细信息解析
"""

from adapters.ascend.common import AscendAdapter
from adapters.ascend.npu import (
    get_npu_info,
    detect_cann_version,
    detect_acl_available,
    parse_npu_smi_info,
)

__all__ = [
    "AscendAdapter",
    "get_npu_info",
    "detect_cann_version",
    "detect_acl_available",
    "parse_npu_smi_info",
]
