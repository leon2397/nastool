# -*- coding: utf-8 -*-
"""GPU/NPU 检测 (declarative style)"""

from __future__ import annotations

import platform

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult


GPU_DEVICES = {
    "/dev/nvidia0": {"name": "NVIDIA GPU", "type": "nvidia_gpu"},
    "/dev/nvidia": {"name": "NVIDIA GPU", "type": "nvidia_gpu"},
    "/dev/rknpu": {"name": "Rockchip NPU", "type": "rockchip_npu"},
    "/dev/davinci0": {"name": "Huawei Ascend NPU", "type": "huawei_ascend"},
    "/dev/davinci": {"name": "Huawei Ascend NPU", "type": "huawei_ascend"},
    "/dev/intel-npu": {"name": "Intel NPU", "type": "intel_npu"},
    "/dev/dri/renderD128": {"name": "GPU (DRI)", "type": "dri_gpu"},
}


@check(
    id="gpu_detected",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="GPU/NPU Detection",
    description="Check if AI accelerator is detected",
    timeout=10,
)
def gpu_detected(ctx: CheckContext) -> CheckResult:
    """检测 GPU/NPU 是否被系统识别"""
    detected = []

    for device_path, info in GPU_DEVICES.items():
        if ctx.file_exists(device_path):
            detected.append({"path": device_path, "name": info["name"], "type": info["type"]})

    # Check for Jetson specifically
    is_jetson = False
    jetson_model = ""
    
    # 方法 1：通过设备树模型检测
    try:
        with open("/proc/device-tree/model", "r") as f:
            jetson_model = f.read().strip()
        if "jetson" in jetson_model.lower():
            is_jetson = True
    except Exception:
        pass
    
    # 方法 2：通过 NVIDIA GPU 检测（备选）
    if not is_jetson:
        try:
            import os
            if os.path.exists("/proc/driver/nvidia/gpus/") and len(os.listdir("/proc/driver/nvidia/gpus/")) > 0:
                is_jetson = True
                jetson_model = "NVIDIA Jetson"
        except Exception:
            pass
    
    # 方法 3：通过 tegrastats 命令检测（备选）
    if not is_jetson:
        try:
            import subprocess
            result = subprocess.run(["which", "tegrastats"], capture_output=True, timeout=5)
            if result.returncode == 0:
                is_jetson = True
                jetson_model = "NVIDIA Jetson"
        except Exception:
            pass
    
    # 方法 4：通过 /dev/nvhost-gpu 检测（备选）
    if not is_jetson:
        try:
            import os
            if os.path.exists("/dev/nvhost-gpu"):
                is_jetson = True
                jetson_model = "NVIDIA Jetson"
        except Exception:
            pass

    if is_jetson:
        if not any(d["type"] == "nvidia_gpu" or d["type"] == "nvidia_jetson" for d in detected):
            detected.append({"path": "/proc/driver/nvidia/gpus/" if os.path.exists("/proc/driver/nvidia/gpus/") else "/dev/nvhost-gpu", "name": jetson_model, "type": "nvidia_jetson"})

    # Check for Apple Silicon
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        detected.append({"path": "sysctl", "name": "Apple Silicon", "type": "apple_silicon"})

    if detected:
        names = [d["name"] for d in detected]
        return ctx.passed(
            current="detected",
            expected="detected",
            message=f"AI accelerator detected: {', '.join(names)}",
            details={"detected": detected},
        )

    return ctx.warning(
        current="none",
        expected="detected",
        message="No AI accelerator detected, will use CPU fallback",
        fix_available=True,
        fix_description="Install GPU/NPU drivers",
    )


# Backward-compatible class alias
GPUDetectedCheck = gpu_detected
