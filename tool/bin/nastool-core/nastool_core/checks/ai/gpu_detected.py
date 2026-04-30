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
    jetson_model = ""
    try:
        with open("/proc/device-tree/model", "r") as f:
            jetson_model = f.read().strip()
    except Exception:
        pass

    if "jetson" in jetson_model.lower():
        if not any(d["type"] == "nvidia_gpu" for d in detected):
            detected.append({"path": "/proc/device-tree/model", "name": jetson_model, "type": "nvidia_jetson"})

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
