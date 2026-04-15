# -*- coding: utf-8 -*-
"""
nastool tests.mock_adapters.rockchip.mock_data - Rockchip Mock 数据

模拟 RK3588/RK356x 设备的系统输出，用于测试解析逻辑。
"""

from __future__ import annotations

from typing import Any

# ------------------------------------------------------------------ #
# RK3588 开发板
# ------------------------------------------------------------------ #

RK3588_DEV: dict[str, Any] = {
    "device_family": "Rockchip",
    "device_model": "RK3588",
    "device_tree_model": "RK3588 Development Board",
    # /dev/rknpu 存在
    "rknpu_exists": True,
    # NPU 固件版本
    "npu_firmware": "v1.3.2",
    # RKNN SDK 库
    "rknn_sdk_lib": "librknn_rknn_api.so",
    # RKNN Runtime 版本
    "rknn_runtime": "1.5.2",
    # 温度
    "thermal_npu": 52.0,
    "thermal_cpu": 48.0,
    # DDR 频率
    "ddr_freq_mhz": "2112.0 MHz",
    # GPU 状态
    "gpu_status": "active",
    # GPU 频率
    "gpu_freq_mhz": "900.0 MHz",
    # NPU 频率
    "npu_freq_mhz": "1000.0 MHz",
    # V4L2 设备
    "v4l2_devices": """rk-h264-decoder (platform:rk-h264-decoder):
	/dev/video0
	/dev/video1

rk-h264-encoder (platform:rk-h264-encoder):
	/dev/video2
	/dev/video3

rk-isp-subdev (platform:rk-isp-subdev):
	/dev/media0

rk-isp-video (platform:rk-isp-video):
	/dev/video4
	/dev/video5""",
    "expected": {
        "rknpu_node": True,
        "npu_firmware": "v1.3.2",
        "rknn_sdk_lib": "librknn_rknn_api.so",
        "rknn_runtime": "1.5.2",
        "thermal_zone7_c": 52.0,
        "thermal_zone8_c": 48.0,
        "ddr_freq_mhz": "2112.0 MHz",
        "gpu_status": "active",
        "gpu_freq_mhz": "900.0 MHz",
        "npu_freq_mhz": "1000.0 MHz",
    },
}

# ------------------------------------------------------------------ #
# RK3568 开发板
# ------------------------------------------------------------------ #

RK3568_DEV: dict[str, Any] = {
    "device_family": "Rockchip",
    "device_model": "RK3568",
    "device_tree_model": "RK3568 Evaluation Board",
    # /dev/rknpu 存在
    "rknpu_exists": True,
    # NPU 固件版本
    "npu_firmware": "v1.2.1",
    # RKNN SDK 库
    "rknn_sdk_lib": "librknn_rknn_api.so",
    # RKNN Runtime 版本（未安装）
    "rknn_runtime": "not_installed",
    # 温度
    "thermal_npu": 45.0,
    "thermal_cpu": 42.0,
    # DDR 频率
    "ddr_freq_mhz": "1560.0 MHz",
    # GPU 状态
    "gpu_status": "active",
    # GPU 频率
    "gpu_freq_mhz": "800.0 MHz",
    # NPU 频率（低版本可能没有）
    "npu_freq_mhz": "unknown",
    # V4L2 设备（较少）
    "v4l2_devices": """rk-isp-video (platform:rk-isp-video):
	/dev/video0
	/dev/video1""",
    "expected": {
        "rknpu_node": True,
        "npu_firmware": "v1.2.1",
        "rknn_sdk_lib": "librknn_rknn_api.so",
        "rknn_runtime": "not_installed",
        "thermal_zone7_c": 45.0,
        "thermal_zone8_c": 42.0,
        "ddr_freq_mhz": "1560.0 MHz",
        "gpu_status": "active",
        "gpu_freq_mhz": "800.0 MHz",
    },
}

# ------------------------------------------------------------------ #
# RK3588 NPU 驱动未加载
# ------------------------------------------------------------------ #

RK3588_NO_NPU: dict[str, Any] = {
    "device_family": "Rockchip",
    "device_model": "RK3588",
    "device_tree_model": "RK3588 Board (NPU not loaded)",
    # /dev/rknpu 不存在
    "rknpu_exists": False,
    # NPU 固件版本
    "npu_firmware": "unknown",
    # RKNN SDK 库
    "rknn_sdk_lib": "unknown",
    # RKNN Runtime 版本
    "rknn_runtime": "not_installed",
    # 温度
    "thermal_npu": 40.0,
    "thermal_cpu": 55.0,
    # DDR 频率
    "ddr_freq_mhz": "528.0 MHz",
    # GPU 状态
    "gpu_status": "idle",
    # GPU 频率
    "gpu_freq_mhz": "200.0 MHz",
    # NPU 频率
    "npu_freq_mhz": "unknown",
    # V4L2 设备
    "v4l2_devices": "none",
    "expected": {
        "rknpu_node": False,
        "npu_firmware": "unknown",
        "rknn_sdk_lib": "unknown",
        "rknn_runtime": "not_installed",
        "gpu_status": "idle",
    },
}

# 导出所有 Mock 数据
ALL_MOCKS = [RK3588_DEV, RK3568_DEV, RK3588_NO_NPU]
