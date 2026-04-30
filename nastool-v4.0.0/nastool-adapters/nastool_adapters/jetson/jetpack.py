# -*- coding: utf-8 -*-
"""
nastool adapters.jetson.jetpack - JetPack 版本映射

JetPack 版本与 CUDA / cuDNN / TensorRT 版本对应关系。

JetPack 6.x (L4T 35.x+):
- JetPack 6.0: CUDA 12.2, cuDNN 8.9, TensorRT 8.6
- JetPack 6.1: CUDA 12.4, cuDNN 9.0, TensorRT 8.6

JetPack 5.x (L4T 34.x-35.x):
- JetPack 5.0: CUDA 11.4, cuDNN 8.4, TensorRT 8.4
- JetPack 5.1: CUDA 11.4, cuDNN 8.6, TensorRT 8.5

JetPack 4.x (L4T 32.x):
- JetPack 4.6: CUDA 10.2, cuDNN 8.2, TensorRT 8.2
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# ------------------------------------------------------------------ #
# JetPack -> CUDA/cuDNN/TensorRT 映射表
# ------------------------------------------------------------------ #

JETPACK_VERSION_MAP: Dict[str, Dict[str, str]] = {
    # JetPack 6.x
    "6.1": {
        "cuda": "12.4",
        "cudnn": "9.0",
        "tensorrt": "8.6.2",
        "l4t": "36.3",
        "ubuntu": "22.04",
    },
    "6.0": {
        "cuda": "12.2",
        "cudnn": "8.9",
        "tensorrt": "8.6.0",
        "l4t": "35.2",
        "ubuntu": "22.04",
    },
    # JetPack 5.x
    "5.1.2": {
        "cuda": "11.4",
        "cudnn": "8.6",
        "tensorrt": "8.5.2",
        "l4t": "35.4",
        "ubuntu": "20.04",
    },
    "5.1.1": {
        "cuda": "11.4",
        "cudnn": "8.6",
        "tensorrt": "8.5.1",
        "l4t": "35.3",
        "ubuntu": "20.04",
    },
    "5.1": {
        "cuda": "11.4",
        "cudnn": "8.6",
        "tensorrt": "8.5.0",
        "l4t": "35.2",
        "ubuntu": "20.04",
    },
    "5.0.2": {
        "cuda": "11.4",
        "cudnn": "8.4",
        "tensorrt": "8.4.1",
        "l4t": "35.1",
        "ubuntu": "20.04",
    },
    "5.0.1": {
        "cuda": "11.4",
        "cudnn": "8.4",
        "tensorrt": "8.4.0",
        "l4t": "35.0",
        "ubuntu": "20.04",
    },
    "5.0": {
        "cuda": "11.4",
        "cudnn": "8.4",
        "tensorrt": "8.4.0",
        "l4t": "34.1",
        "ubuntu": "20.04",
    },
    # JetPack 4.x
    "4.6.4": {
        "cuda": "10.2",
        "cudnn": "8.2",
        "tensorrt": "8.2.1",
        "l4t": "32.7",
        "ubuntu": "18.04",
    },
    "4.6.3": {
        "cuda": "10.2",
        "cudnn": "8.2",
        "tensorrt": "8.2.1",
        "l4t": "32.7",
        "ubuntu": "18.04",
    },
    "4.6.2": {
        "cuda": "10.2",
        "cudnn": "8.2",
        "tensorrt": "8.2.1",
        "l4t": "32.7",
        "ubuntu": "18.04",
    },
    "4.6.1": {
        "cuda": "10.2",
        "cudnn": "8.2",
        "tensorrt": "8.0.1",
        "l4t": "32.7",
        "ubuntu": "18.04",
    },
    "4.6": {
        "cuda": "10.2",
        "cudnn": "8.2",
        "tensorrt": "8.0.1",
        "l4t": "32.6",
        "ubuntu": "18.04",
    },
    "4.5.1": {
        "cuda": "10.2",
        "cudnn": "8.0",
        "tensorrt": "8.0.1",
        "l4t": "32.5",
        "ubuntu": "18.04",
    },
    "4.5": {
        "cuda": "10.2",
        "cudnn": "8.0",
        "tensorrt": "8.0.0",
        "l4t": "32.5",
        "ubuntu": "18.04",
    },
    "4.4.1": {
        "cuda": "10.0",
        "cudnn": "8.0",
        "tensorrt": "7.1.3",
        "l4t": "32.4",
        "ubuntu": "18.04",
    },
    "4.4": {
        "cuda": "10.0",
        "cudnn": "8.0",
        "tensorrt": "7.1.3",
        "l4t": "32.4",
        "ubuntu": "18.04",
    },
}

# 设备族支持的 JetPack 版本
DEVICE_JETPACK_SUPPORT: Dict[str, List[str]] = {
    "Orin AGX": ["6.1", "6.0", "5.1.2", "5.1.1", "5.1", "5.0.2", "5.0.1", "5.0"],
    "Orin NX": ["6.1", "6.0", "5.1.2", "5.1.1", "5.1", "5.0.2", "5.0.1", "5.0"],
    "Orin Nano": ["6.1", "6.0", "5.1.2", "5.1.1", "5.1", "5.0.2", "5.0.1", "5.0"],
    "AGX Xavier": ["5.1.2", "5.1.1", "5.1", "5.0.2", "5.0.1", "5.0", "4.6.4", "4.6.3", "4.6.2", "4.6.1", "4.6"],
    "Xavier NX": ["5.1.2", "5.1.1", "5.1", "5.0.2", "5.0.1", "5.0", "4.6.4", "4.6.3", "4.6.2", "4.6.1", "4.6"],
    "Nano/TX2": ["4.6.4", "4.6.3", "4.6.2", "4.6.1", "4.6", "4.5.1", "4.5", "4.4.1", "4.4"],
}


def get_jetpack_info(version: str) -> Optional[Dict[str, str]]:
    """
    获取 JetPack 版本对应的 CUDA/cuDNN/TensorRT 版本。

    Args:
        version: JetPack 版本（如 "5.1", "6.0"）

    Returns:
        {"cuda": "...", "cudnn": "...", "tensorrt": "..."} 或 None
    """
    return JETPACK_VERSION_MAP.get(version)


def get_latest_jetpack(device_family: str) -> Optional[str]:
    """
    获取设备族支持的最新 JetPack 版本。

    Args:
        device_family: 设备族名称

    Returns:
        版本号字符串或 None
    """
    versions = DEVICE_JETPACK_SUPPORT.get(device_family, [])
    return versions[0] if versions else None


def check_version_compatibility(
    device_family: str,
    jetpack_version: str,
    cuda_version: Optional[str] = None,
    tensorrt_version: Optional[str] = None,
) -> Dict[str, bool]:
    """
    检查版本兼容性。

    Args:
        device_family: 设备族
        jetpack_version: JetPack 版本
        cuda_version: 实际 CUDA 版本
        tensorrt_version: 实际 TensorRT 版本

    Returns:
        {"jetpack_supported": bool, "cuda_match": bool, "tensorrt_match": bool}
    """
    result = {
        "jetpack_supported": False,
        "cuda_match": None,
        "tensorrt_match": None,
    }

    # 检查 JetPack 是否支持
    supported = DEVICE_JETPACK_SUPPORT.get(device_family, [])
    result["jetpack_supported"] = jetpack_version in supported

    # 获取预期版本
    expected = get_jetpack_info(jetpack_version)
    if expected:
        if cuda_version:
            result["cuda_match"] = cuda_version.startswith(expected["cuda"].split(".")[0])
        if tensorrt_version:
            result["tensorrt_match"] = tensorrt_version.startswith(expected["tensorrt"].split(".")[0])

    return result


def l4t_to_jetpack(l4t_version: str) -> Optional[str]:
    """
    从 L4T 版本推断 JetPack 版本。

    Args:
        l4t_version: L4T 版本（如 "35.2", "32.7"）

    Returns:
        JetPack 版本或 None
    """
    # L4T 版本映射
    l4t_to_jp = {
        "36": "6.1",
        "35.4": "5.1.2",
        "35.3": "5.1.1",
        "35.2": "5.1",
        "35.1": "5.0.2",
        "35.0": "5.0.1",
        "34": "5.0",
        "32.7": "4.6.4",
        "32.6": "4.6",
        "32.5": "4.5",
        "32.4": "4.4",
    }

    for l4t_prefix, jetpack in l4t_to_jp.items():
        if l4t_version.startswith(l4t_prefix):
            return jetpack

    return None
