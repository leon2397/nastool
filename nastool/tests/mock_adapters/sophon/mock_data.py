# -*- coding: utf-8 -*-
"""
nastool tests.mock_adapters.sophon.mock_data - SOPHON Mock 数据

模拟 BM1688/BM1684/BM1690 设备的系统输出，用于测试解析逻辑。
"""

from __future__ import annotations

from typing import Any

# ------------------------------------------------------------------ #
# BM1688 服务器卡
# ------------------------------------------------------------------ #

BM1688_DEV: dict[str, Any] = {
    "device_family": "SOPHON",
    "device_model": "BM1688",
    "device_tree_model": "Sophon BM1688 PCIe Card",
    # SDK 版本
    "sophon_sdk_version": "v3.4.1",
    # TPU 设备
    "tpu_devices": "/dev/bmdev0\n/dev/bmdev1\n/dev/bmdev2\n/dev/bmdev3",
    "tpu_available": True,
    # 编译器和运行时
    "bmcompiler_version": "v3.4.1",
    "bmruntime_version": "v3.4.0",
    # Python 库
    "sophon_python_version": "3.4.1",
    "bmtorch_version": "1.3.0",
    # SAIL
    "sail_version": "3.4.1",
    # BMChip 类型
    "chip_type": "BM1688",
    # PCIe 设备
    "pcie_devices": "81:00.0 Processing accelerators: Sophgo BM1688 (asic)",
    # Docker TPU 镜像
    "docker_tpu_images": "sophonai/sophon-tpuvim:latest",
    # VPU 编解码
    "vpu_decode": "H.264/H.265 8K Decode",
    "vpu_encode": "H.264/H.265 4K Encode",
    "expected": {
        "sophon_sdk_version": "v3.4.1",
        "tpu_available": True,
        "bmcompiler_version": "v3.4.1",
        "bmruntime_version": "v3.4.0",
        "sophon_python_version": "3.4.1",
        "sail_version": "3.4.1",
        "chip_type": "BM1688",
    },
}

# ------------------------------------------------------------------ #
# BM1684 边缘设备
# ------------------------------------------------------------------ #

BM1684_DEV: dict[str, Any] = {
    "device_family": "SOPHON",
    "device_model": "BM1684",
    "device_tree_model": "Sophon BM1684 Edge Device",
    # SDK 版本
    "sophon_sdk_version": "v3.2.0",
    # TPU 设备
    "tpu_devices": "/dev/bmdev0",
    "tpu_available": True,
    # 编译器和运行时
    "bmcompiler_version": "v3.2.0",
    "bmruntime_version": "v3.2.0",
    # Python 库
    "sophon_python_version": "3.2.0",
    "bmtorch_version": "1.2.0",
    # SAIL（未安装）
    "sail_version": "",
    # BMChip 类型
    "chip_type": "BM1684",
    # PCIe 设备
    "pcie_devices": "",
    # Docker TPU 镜像
    "docker_tpu_images": "",
    # VPU 编解码
    "vpu_decode": "H.264/H.265 4K Decode",
    "vpu_encode": "H.264/H.265 1080p Encode",
    "expected": {
        "sophon_sdk_version": "v3.2.0",
        "tpu_available": True,
        "bmcompiler_version": "v3.2.0",
        "bmruntime_version": "v3.2.0",
        "sophon_python_version": "3.2.0",
    },
}

# ------------------------------------------------------------------ #
# SE5 智能边缘盒（驱动未加载）
# ------------------------------------------------------------------ #

SE5_NO_TPU: dict[str, Any] = {
    "device_family": "SOPHON",
    "device_model": "SE5",
    "device_tree_model": "Sophon SE5 Edge Box",
    # SDK 版本
    "sophon_sdk_version": "",
    # TPU 设备（不存在）
    "tpu_devices": "",
    "tpu_available": False,
    # 编译器和运行时
    "bmcompiler_version": "",
    "bmruntime_version": "",
    # Python 库
    "sophon_python_version": "",
    "bmtorch_version": "",
    # SAIL
    "sail_version": "",
    # BMChip 类型
    "chip_type": "unknown",
    # PCIe 设备
    "pcie_devices": "",
    # Docker TPU 镜像
    "docker_tpu_images": "sophonai/sophon-tpuvim:latest",
    # VPU 编解码
    "vpu_decode": "",
    "vpu_encode": "",
    "expected": {
        "sophon_sdk_version": "",
        "tpu_available": False,
        "bmcompiler_version": "",
        "bmruntime_version": "",
    },
}

# 导出所有 Mock 数据
ALL_MOCKS = [BM1688_DEV, BM1684_DEV, SE5_NO_TPU]
