# -*- coding: utf-8 -*-
"""
nastool tests.mock_adapters.jetson.mock_data - Jetson Mock 数据

模拟 6 类设备的 tegrastats 输出，用于测试解析逻辑。
"""

from __future__ import annotations

from typing import Any

# ------------------------------------------------------------------ #
# Orin AGX（Ada，275/170TOPS）
# ------------------------------------------------------------------ #

ORIN_AGX_64GB: dict[str, Any] = {
    "device_family": "Orin AGX",
    "device_model": "NVIDIA Jetson AGX Orin 64GB",
    "device_tree_model": "NVIDIA Jetson AGX Orin 64GB",
    "tegrastats": """RAM 12543/63488MB (lfb 4218x4MB) CPU [5%@2265,3%@2265,2%@2265,2%@2265,4%@2265,3%@2265,2%@2265,1%@2265] EMC_FREQ 2133 GR3D_FREQ 0%@1300 APE 150 MTS fg:0 bg:0 AO: avg:0 std:0 MC: 0 MC: 0 POM_5V_IN 13021mW/13021mW VDD_IN 12500mW/12500mW
""",
    "jetpack_version": "6.0",
    "cuda_version": "12.2",
    "tensorrt_version": "8.6.2",
    "expected": {
        "ram_used_mb": 12543,
        "ram_total_mb": 63488,
        "cpu_util_pct": 2.75,  # avg of 5+3+2+2+4+3+2+1 / 8
        "gpu_util_pct": 0,
    },
}

ORIN_AGX_32GB: dict[str, Any] = {
    "device_family": "Orin AGX",
    "device_model": "NVIDIA Jetson AGX Orin 32GB",
    "device_tree_model": "NVIDIA Jetson AGX Orin 32GB",
    "tegrastats": """RAM 8234/31652MB (lfb 3722x4MB) CPU [3%@1374,5%@1375,4%@1374,4%@1376] EMC_FREQ 2133 GR3D_FREQ 45%@1300 APE 150
""",
    "jetpack_version": "5.1.3",
    "cuda_version": "11.4",
    "expected": {
        "ram_total_mb": 31652,
        "gpu_util_pct": 45,
    },
}

# ------------------------------------------------------------------ #
# Orin NX（Ada，100/70TOPS）
# ------------------------------------------------------------------ #

ORIN_NX_16GB: dict[str, Any] = {
    "device_family": "Orin NX",
    "device_model": "NVIDIA Jetson Orin NX 16GB",
    "device_tree_model": "NVIDIA Jetson Orin NX 16GB",
    "tegrastats": """RAM 4521/15180MB (lfb 2845x4MB) CPU [12%@2100,8%@2100,10%@2100,14%@2100,11%@2100,9%@2100] EMC_FREQ 2133 GR3D_FREQ 78%@1300
""",
    "jetpack_version": "6.0",
    "cuda_version": "12.2",
    "expected": {
        "ram_total_mb": 15180,
        "gpu_util_pct": 78,
    },
}

ORIN_NX_8GB: dict[str, Any] = {
    "device_family": "Orin NX",
    "device_model": "NVIDIA Jetson Orin NX 8GB",
    "device_tree_model": "NVIDIA Jetson Orin NX 8GB",
    "tegrastats": """RAM 3210/7580MB (lfb 1212x4MB) CPU [5%@2100,3%@2100,4%@2100,6%@2100,5%@2100,4%@2100] EMC_FREQ 2133 GR3D_FREQ 22%@1300
""",
    "expected": {
        "ram_total_mb": 7580,
    },
}

# ------------------------------------------------------------------ #
# Orin Nano（Ada，40/20TOPS）
# ------------------------------------------------------------------ #

ORIN_NANO_8GB: dict[str, Any] = {
    "device_family": "Orin Nano",
    "device_model": "NVIDIA Jetson Orin Nano 8GB",
    "device_tree_model": "NVIDIA Jetson Orin Nano 8GB",
    "tegrastats": """RAM 2845/7580MB (lfb 1024x4MB) CPU [8%@2100,6%@2100,5%@2100,7%@2100] EMC_FREQ 2133 GR3D_FREQ 35%@1300
""",
    "jetpack_version": "6.0",
    "expected": {
        "ram_total_mb": 7580,
        "gpu_util_pct": 35,
    },
}

ORIN_NANO_4GB: dict[str, Any] = {
    "device_family": "Orin Nano",
    "device_model": "NVIDIA Jetson Orin Nano 4GB",
    "device_tree_model": "NVIDIA Jetson Orin Nano 4GB",
    "tegrastats": """RAM 1523/3964MB (lfb 512x4MB) CPU [10%@2100,8%@2100,9%@2100,11%@2100] EMC_FREQ 2133 GR3D_FREQ 42%@1300
""",
    "expected": {
        "ram_total_mb": 3964,
    },
}

# ------------------------------------------------------------------ #
# AGX Xavier（Volta，11TOPS）
# ------------------------------------------------------------------ #

AGX_XAVIER_64GB: dict[str, Any] = {
    "device_family": "AGX Xavier",
    "device_model": "NVIDIA Jetson AGX Xavier 64GB",
    "device_tree_model": "NVIDIA Jetson AGX Xavier 64GB",
    "tegrastats": """RAM 7813/63488MB (lfb 3722x4MB) CPU [3%@1374,5%@1375,4%@1374,4%@1376] EMC_FREQ 2133 GR3D_FREQ 0%@1377
""",
    "jetpack_version": "5.1.2",
    "cuda_version": "11.4",
    "expected": {
        "ram_total_mb": 63488,
    },
}

AGX_XAVIER_32GB: dict[str, Any] = {
    "device_family": "AGX Xavier",
    "device_model": "NVIDIA Jetson AGX Xavier 32GB",
    "device_tree_model": "NVIDIA Jetson AGX Xavier 32GB",
    "tegrastats": """RAM 4521/31652MB (lfb 2100x4MB) CPU [2%@1900,3%@1900,4%@1900,5%@1900,2%@1900,3%@1900,4%@1900,5%@1900] EMC_FREQ 2133 GR3D_FREQ 15%@1377
""",
    "expected": {
        "ram_total_mb": 31652,
        "gpu_util_pct": 15,
    },
}

# ------------------------------------------------------------------ #
# Xavier NX（Volta，6TOPS）
# ------------------------------------------------------------------ #

XAVIER_NX: dict[str, Any] = {
    "device_family": "Xavier NX",
    "device_model": "NVIDIA Jetson Xavier NX",
    "device_tree_model": "NVIDIA Jetson Xavier NX",
    "tegrastats": """RAM 3241/7864MB (lfb 1345x4MB) CPU [8%@1900,6%@1900,5%@1900,4%@1900,7%@1900,6%@1900] EMC_FREQ 1600 GR3D_FREQ 52%@1300
""",
    "jetpack_version": "5.1.2",
    "cuda_version": "11.4",
    "expected": {
        "ram_total_mb": 7864,
        "gpu_util_pct": 52,
    },
}

# ------------------------------------------------------------------ #
# Nano/TX2（Maxwell/Pascal）
# ------------------------------------------------------------------ #

JETSON_NANO: dict[str, Any] = {
    "device_family": "Nano/TX2",
    "device_model": "NVIDIA Jetson Nano",
    "device_tree_model": "NVIDIA Jetson Nano",
    # JetPack 4.x 老格式
    "tegrastats": """RAM: 3241MB / 3964MB | CPU: [23.4%] | TEMP: 38.7C | VDD: 4432mV / 4418mV
""",
    "jetpack_version": "4.6",
    "cuda_version": "10.2",
    "expected": {
        "ram_used_mb": 3241,
        "ram_total_mb": 3964,
        "cpu_util_pct": 23.4,
        "temperature_c": 38.7,
    },
}

JETSON_TX2: dict[str, Any] = {
    "device_family": "Nano/TX2",
    "device_model": "NVIDIA Jetson TX2",
    "device_tree_model": "NVIDIA Jetson TX2",
    "tegrastats": """RAM: 5823MB / 7864MB | CPU: [18.5%] | TEMP: 42.3C | VDD: 5210mV / 4890mV
""",
    "jetpack_version": "4.6",
    "expected": {
        "ram_total_mb": 7864,
    },
}

# ------------------------------------------------------------------ #
# 汇总
# ------------------------------------------------------------------ #

ALL_JETSON_MOCKS: list[dict[str, Any]] = [
    ORIN_AGX_64GB,
    ORIN_AGX_32GB,
    ORIN_NX_16GB,
    ORIN_NX_8GB,
    ORIN_NANO_8GB,
    ORIN_NANO_4GB,
    AGX_XAVIER_64GB,
    AGX_XAVIER_32GB,
    XAVIER_NX,
    JETSON_NANO,
    JETSON_TX2,
]

# 按设备族分组
BY_FAMILY: dict[str, list[dict[str, Any]]] = {
    "Orin AGX": [ORIN_AGX_64GB, ORIN_AGX_32GB],
    "Orin NX": [ORIN_NX_16GB, ORIN_NX_8GB],
    "Orin Nano": [ORIN_NANO_8GB, ORIN_NANO_4GB],
    "AGX Xavier": [AGX_XAVIER_64GB, AGX_XAVIER_32GB],
    "Xavier NX": [XAVIER_NX],
    "Nano/TX2": [JETSON_NANO, JETSON_TX2],
}
