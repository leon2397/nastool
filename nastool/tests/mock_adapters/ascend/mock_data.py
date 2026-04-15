# -*- coding: utf-8 -*-
"""
nastool tests.mock_adapters.ascend.mock_data - 昇腾 Mock 数据

模拟 4 类设备的 npu-smi 输出，用于测试解析逻辑。
"""

from __future__ import annotations

from typing import Any

# ------------------------------------------------------------------ #
# Atlas 200系（嵌入式模组/开发板）
# ------------------------------------------------------------------ #

ATLAS_200I_A2: dict[str, Any] = {
    "device_family": "Atlas 200系",
    "device_model": "Atlas 200I A2",
    "device_tree_model": "Atlas 200I A2",
    "npu_smi_list": """Card 0 [Ascend 310]
""",
    "npu_smi_query": """NPU ID                               : 0
Chip Name                            : Ascend 310
Chip Type                            : Ascend 310
Health Status                        : OK
Chip Temperature(C)                  : 58
NPU Utilization(%)                   : 23
Memory Total(MB)                     : 8192
Memory Used(MB)                      : 2048
Memory Free(MB)                      : 6144
Power Consumption(W)                 : 8.5
Chip Frequency(MHz)                  : 1000
""",
    "expected": {
        "device_count": 1,
        "chip": "Ascend 310",
        "temperature": 58,
        "utilization": 23,
        "memory_total_mb": 8192,
        "memory_used_mb": 2048,
    },
}

ATLAS_200DK_A2: dict[str, Any] = {
    "device_family": "Atlas 200系",
    "device_model": "Atlas 200DK A2",
    "device_tree_model": "Atlas 200DK A2",
    "npu_smi_list": """Card 0 [Ascend 310]
""",
    "npu_smi_query": """NPU ID                               : 0
Chip Name                            : Ascend 310
Health Status                        : OK
Chip Temperature(C)                  : 52
NPU Utilization(%)                   : 15
Memory Total(MB)                     : 8192
Memory Used(MB)                      : 1024
Memory Free(MB)                      : 7168
Power Consumption(W)                 : 6.2
""",
    "expected": {
        "device_count": 1,
        "chip": "Ascend 310",
        "temperature": 52,
        "utilization": 15,
    },
}

# ------------------------------------------------------------------ #
# Atlas 300系（PCIe 推理卡）
# ------------------------------------------------------------------ #

ATLAS_300I_PRO: dict[str, Any] = {
    "device_family": "Atlas 300系",
    "device_model": "Atlas 300I Pro",
    "device_tree_model": "Atlas 300I Pro",
    "npu_smi_list": """Card 0 [Ascend 310P3]
Card 1 [Ascend 310P3]
Card 2 [Ascend 310P3]
Card 3 [Ascend 310P3]
""",
    "npu_smi_query": """NPU ID                               : 0
Chip Name                            : Ascend 310P3
Health Status                        : OK
Chip Temperature(C)                  : 68
NPU Utilization(%)                   : 85
Memory Total(MB)                     : 32768
Memory Used(MB)                      : 24576
Memory Free(MB)                      : 8192
Power Consumption(W)                 : 62.5
Chip Frequency(MHz)                  : 1500
""",
    "expected": {
        "device_count": 4,
        "chip": "Ascend 310P3",
        "temperature": 68,
        "utilization": 85,
        "memory_total_mb": 32768,
    },
}

ATLAS_300I_DUO: dict[str, Any] = {
    "device_family": "Atlas 300系",
    "device_model": "Atlas 300I Duo",
    "device_tree_model": "Atlas 300I Duo",
    "npu_smi_list": """Card 0 [Ascend 310P3]
Card 1 [Ascend 310P3]
""",
    "npu_smi_query": """NPU ID                               : 0
Chip Name                            : Ascend 310P3
Health Status                        : OK
Chip Temperature(C)                  : 65
NPU Utilization(%)                   : 72
Memory Total(MB)                     : 32768
Memory Used(MB)                      : 16384
Power Consumption(W)                 : 48.0
""",
    "expected": {
        "device_count": 2,
        "chip": "Ascend 310P3",
    },
}

ATLAS_300V_SHOUGUANG: dict[str, Any] = {
    "device_family": "Atlas 300系",
    "device_model": "Atlas 300V 寿光卡",
    "device_tree_model": "Atlas 300V",
    "npu_smi_list": """Card 0 [Ascend 910A]
""",
    "npu_smi_query": """NPU ID                               : 0
Chip Name                            : Ascend 910A
Health Status                        : OK
Chip Temperature(C)                  : 72
NPU Utilization(%)                   : 45
Memory Total(MB)                     : 65536
Memory Used(MB)                      : 32768
Power Consumption(W)                 : 250.0
""",
    "expected": {
        "device_count": 1,
        "chip": "Ascend 910A",
        "memory_total_mb": 65536,
    },
}

# ------------------------------------------------------------------ #
# Atlas 500系（边缘小站）
# ------------------------------------------------------------------ #

ATLAS_500_A2: dict[str, Any] = {
    "device_family": "Atlas 500系",
    "device_model": "Atlas 500 A2",
    "device_tree_model": "Atlas 500 A2",
    "npu_smi_list": """Card 0 [Ascend 310P]
""",
    "npu_smi_query": """NPU ID                               : 0
Chip Name                            : Ascend 310P
Health Status                        : OK
Chip Temperature(C)                  : 55
NPU Utilization(%)                   : 30
Memory Total(MB)                     : 16384
Memory Used(MB)                      : 4096
Power Consumption(W)                 : 15.0
""",
    "expected": {
        "device_count": 1,
        "chip": "Ascend 310P",
    },
}

# ------------------------------------------------------------------ #
# Atlas A2 Lite系（新代际边缘）
# ------------------------------------------------------------------ #

ATLAS_A2_SMART_STATION: dict[str, Any] = {
    "device_family": "Atlas A2 Lite系",
    "device_model": "Atlas A2 智能小站",
    "device_tree_model": "Atlas A2 智能小站",
    "npu_smi_list": """Card 0 [Ascend 310P]
""",
    "npu_smi_query": """NPU ID                               : 0
Chip Name                            : Ascend 310P
Health Status                        : OK
Chip Temperature(C)                  : 48
NPU Utilization(%)                   : 12
Memory Total(MB)                     : 32768
Memory Used(MB)                      : 2048
Power Consumption(W)                 : 10.5
""",
    "expected": {
        "device_count": 1,
        "chip": "Ascend 310P",
        "temperature": 48,
    },
}

ATLAS_A2_GATEWAY: dict[str, Any] = {
    "device_family": "Atlas A2 Lite系",
    "device_model": "Atlas A2 边缘计算网关",
    "device_tree_model": "Atlas A2 边缘计算网关",
    "npu_smi_list": """Card 0 [Ascend 310P]
""",
    "npu_smi_query": """NPU ID                               : 0
Chip Name                            : Ascend 310P
Health Status                        : OK
Chip Temperature(C)                  : 50
NPU Utilization(%)                   : 18
Memory Total(MB)                     : 16384
Memory Used(MB)                      : 2048
Power Consumption(W)                 : 8.5
""",
    "expected": {
        "device_count": 1,
        "temperature": 50,
    },
}

# ------------------------------------------------------------------ #
# 汇总
# ------------------------------------------------------------------ #

ALL_ASCEND_MOCKS: list[dict[str, Any]] = [
    ATLAS_200I_A2,
    ATLAS_200DK_A2,
    ATLAS_300I_PRO,
    ATLAS_300I_DUO,
    ATLAS_300V_SHOUGUANG,
    ATLAS_500_A2,
    ATLAS_A2_SMART_STATION,
    ATLAS_A2_GATEWAY,
]

# 按设备族分组
BY_FAMILY: dict[str, list[dict[str, Any]]] = {
    "Atlas 200系": [ATLAS_200I_A2, ATLAS_200DK_A2],
    "Atlas 300系": [ATLAS_300I_PRO, ATLAS_300I_DUO, ATLAS_300V_SHOUGUANG],
    "Atlas 500系": [ATLAS_500_A2],
    "Atlas A2 Lite系": [ATLAS_A2_SMART_STATION, ATLAS_A2_GATEWAY],
}
