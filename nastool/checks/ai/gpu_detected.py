"""
checks/ai/gpu_detected.py - GPU/NPU detection check
"""

import os
from ..base import Check, CheckResult, CheckCategory, CheckSeverity
from ..registry import register_check


@register_check
class GPUDetectedCheck(Check):
    """Check if GPU/NPU is detected"""

    check_id = "gpu_detected"
    category = CheckCategory.AI
    title = "GPU/NPU Detection"
    description = "Check if AI accelerator is detected"

    GPU_DEVICES = {
        "/dev/nvidia0": {"name": "NVIDIA GPU", "type": "nvidia_gpu"},
        "/dev/nvidia": {"name": "NVIDIA GPU", "type": "nvidia_gpu"},
        "/dev/rknpu": {"name": "Rockchip NPU", "type": "rockchip_npu"},
        "/dev/davinci0": {"name": "Huawei Ascend NPU", "type": "huawei_ascend"},
        "/dev/davinci": {"name": "Huawei Ascend NPU", "type": "huawei_ascend"},
        "/dev/intel-npu": {"name": "Intel NPU", "type": "intel_npu"},
        "/dev/dri/renderD128": {"name": "GPU (DRI)", "type": "dri_gpu"},
    }

    def run(self) -> CheckResult:
        detected = []

        for device_path, info in self.GPU_DEVICES.items():
            if self._file_exists(device_path):
                detected.append(
                    {
                        "path": device_path,
                        "name": info["name"],
                        "type": info["type"],
                    }
                )

        # Check for Jetson specifically
        jetson_model = ""
        try:
            with open("/proc/device-tree/model", "r") as f:
                jetson_model = f.read().strip()
        except Exception as e:
            pass  # TODO: 添加日志

        if "jetson" in jetson_model.lower():
            if not any(d["type"] == "nvidia_gpu" for d in detected):
                detected.append(
                    {
                        "path": "/proc/device-tree/model",
                        "name": jetson_model,
                        "type": "nvidia_jetson",
                    }
                )

        # Check for Apple Silicon
        import platform

        if platform.system() == "Darwin" and platform.machine() == "arm64":
            detected.append(
                {
                    "path": "sysctl",
                    "name": "Apple Silicon",
                    "type": "apple_silicon",
                }
            )

        if detected:
            severity = CheckSeverity.PASSED
            passed = True
            names = [d["name"] for d in detected]
            message = f"AI accelerator detected: {', '.join(names)}"
        else:
            severity = CheckSeverity.WARNING
            passed = True  # Not critical, CPU fallback works
            message = "No AI accelerator detected, will use CPU fallback"

        return CheckResult(
            check_id=self.check_id,
            category=self.category,
            severity=severity,
            passed=passed,
            title=self.title,
            current="detected" if detected else "none",
            expected="detected",
            message=message,
            fix_available=not detected,
            fix_description="Install GPU/NPU drivers" if not detected else None,
            fix_risk="medium",
            details={"detected": detected},
        )
