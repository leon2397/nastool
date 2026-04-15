"""
checks/ai/version_checker.py - AI component version checker
"""

import os
import re
import sys
from checks.base import Check, CheckResult, CheckCategory, CheckSeverity
from checks.registry import register_check
from core.version_check import VersionDB, compare_versions


# Backward compatibility alias - resolved at access time
class AIVersionCheck(Check):
    """Base class for AI component version checks"""

    category = CheckCategory.AI

    def __init__(self):
        super().__init__()
        self.version_db = VersionDB()
        self.version_db.load()

    def _check_version(self, component: str, current: str, device_model: str = None) -> CheckResult:
        """
        Compare current version against database.

        Args:
            component: Component name (e.g., "nvidia_driver", "cuda")
            current: Current installed version
            device_model: Device model for compatibility check (e.g., "jetson-xavier-nx")

        Returns:
            CheckResult with version comparison
        """
        version_info = self.version_db.get_version(component)

        if not version_info:
            return CheckResult(
                check_id=f"{component}_version",
                category=self.category,
                severity=CheckSeverity.INFO,
                passed=True,
                title=f"{component} Version",
                current=current,
                expected="unknown",
                message=f"{component} version {current} installed (version database not available)",
            )

        latest = version_info.latest
        min_recommended = version_info.min_recommended

        # Check device compatibility
        max_version = None
        if device_model and version_info.compatibility:
            compat = version_info.compatibility.get(device_model, {})
            max_version = compat.get("max")

        # Compare versions
        cmp_latest = compare_versions(current, latest)
        cmp_min = compare_versions(current, min_recommended)

        if cmp_min < 0:
            severity = CheckSeverity.CRITICAL
            passed = False
            message = f"{component} {current} is below minimum recommended {min_recommended}"
        elif cmp_latest < 0:
            severity = CheckSeverity.WARNING
            passed = True
            message = f"{component} {current} can be upgraded to {latest}"
        else:
            severity = CheckSeverity.PASSED
            passed = True
            message = f"{component} {current} is up to date"

        # Check max compatibility
        if max_version and compare_versions(current, max_version) > 0:
            severity = CheckSeverity.WARNING
            passed = True
            message = f"{component} {current} may not be fully compatible with {device_model} (max: {max_version})"

        return CheckResult(
            check_id=f"{component}_version",
            category=self.category,
            severity=severity,
            passed=passed,
            title=f"{component} Version",
            current=current,
            expected=f">= {min_recommended}",
            message=message,
            fix_available=cmp_latest < 0,
            fix_description=f"Upgrade {component} to {latest}",
            fix_risk="medium",
            url=version_info.url,
            details={
                "latest": latest,
                "min_recommended": min_recommended,
                "release_notes": version_info.release_notes,
                "release_date": version_info.release_date,
            },
        )


@register_check
class NvidiaDriverVersionCheck(AIVersionCheck):
    """Check NVIDIA driver version"""

    check_id = "nvidia_driver_version"
    title = "NVIDIA Driver Version"
    description = "Check if NVIDIA driver is up to date"

    def run(self) -> CheckResult:
        # Check if nvidia-smi exists
        if not self._command_exists("nvidia-smi"):
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.INFO,
                passed=True,
                title=self.title,
                current="not installed",
                expected="installed",
                message="NVIDIA driver not detected",
            )

        # Get driver version
        output = self._run_command(
            "nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1"
        )
        if not output:
            output = self._run_command(
                "nvidia-smi 2>/dev/null | grep 'Driver Version' | awk '{print $6}'"
            )

        current = output.strip() if output else "unknown"

        if current == "unknown":
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.WARNING,
                passed=True,
                title=self.title,
                current="unknown",
                expected="detectable",
                message="NVIDIA driver installed but version could not be determined",
            )

        return self._check_version("nvidia_driver", current)


@register_check
class CudaVersionCheck(AIVersionCheck):
    """Check CUDA version"""

    check_id = "cuda_version"
    title = "CUDA Version"
    description = "Check if CUDA is installed and up to date"

    def run(self) -> CheckResult:
        # Check nvcc
        if not self._command_exists("nvcc"):
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.INFO,
                passed=True,
                title=self.title,
                current="not installed",
                expected="installed",
                message="CUDA toolkit not detected (nvcc not found)",
            )

        # Get CUDA version
        output = self._run_command(
            "nvcc --version 2>/dev/null | grep 'release' | awk '{print $5}' | tr -d ','"
        )
        current = output.strip() if output else "unknown"

        if current == "unknown":
            # Try alternative method
            output = self._run_command(
                "cat /usr/local/cuda/version.txt 2>/dev/null | awk '{print $3}'"
            )
            current = output.strip() if output else "unknown"

        return self._check_version("cuda", current)


@register_check
class TensorRTVersionCheck(AIVersionCheck):
    """Check TensorRT version"""

    check_id = "tensorrt_version"
    title = "TensorRT Version"
    description = "Check if TensorRT is installed and up to date"

    def run(self) -> CheckResult:
        # Try Python import
        try:
            import tensorrt

            current = tensorrt.__version__
        except ImportError:
            # Check via command line
            output = self._run_command("trtexec --version 2>/dev/null | head -1")
            if output:
                match = re.search(r"(\d+\.\d+\.\d+)", output)
                current = match.group(1) if match else "unknown"
            else:
                return CheckResult(
                    check_id=self.check_id,
                    category=self.category,
                    severity=CheckSeverity.INFO,
                    passed=True,
                    title=self.title,
                    current="not installed",
                    expected="installed",
                    message="TensorRT not detected",
                )

        return self._check_version("tensorrt", current)


@register_check
class JetPackVersionCheck(AIVersionCheck):
    """Check JetPack version (Jetson devices)"""

    check_id = "jetpack_version"
    title = "JetPack Version"
    description = "Check JetPack version on NVIDIA Jetson devices"

    def run(self) -> CheckResult:
        # Check if Jetson
        jetson_model = ""
        try:
            with open("/proc/device-tree/model", "r") as f:
                jetson_model = f.read().strip().lower()
        except Exception as e:
            pass  # TODO: 添加日志

        if "jetson" not in jetson_model:
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.INFO,
                passed=True,
                title=self.title,
                current="n/a",
                expected="n/a",
                message="Not a Jetson device",
            )

        # Get JetPack version
        current = "unknown"

        # Method 1: jetson-release
        output = self._run_command("jetson-release 2>/dev/null | grep 'JetPack' | awk '{print $2}'")
        if output:
            current = output.strip()
        else:
            # Method 2: check L4T version
            output = self._run_command("cat /etc/nv_tegra_release 2>/dev/null | head -1")
            if output:
                # Map L4T to JetPack
                l4t_to_jp = {
                    "35.1": "5.0.2",
                    "35.2": "5.1",
                    "35.3": "5.1.1",
                    "35.4": "5.1.2",
                    "35.5": "5.1.3",
                    "36.2": "6.0",
                    "36.3": "6.1",
                    "36.4": "6.2",
                }
                for l4t, jp in l4t_to_jp.items():
                    if l4t in output:
                        current = jp
                        break

        # Determine device model
        device_model = "jetson-unknown"
        if "nano" in jetson_model:
            device_model = "jetson-nano"
        elif "xavier-nx" in jetson_model:
            device_model = "jetson-xavier-nx"
        elif "agx-xavier" in jetson_model:
            device_model = "jetson-agx-xavier"
        elif "tx2" in jetson_model:
            device_model = "jetson-tx2"
        elif "orin-nx" in jetson_model:
            device_model = "jetson-orin-nx"
        elif "orin-nano" in jetson_model:
            device_model = "jetson-orin-nano"
        elif "agx-orin" in jetson_model:
            device_model = "jetson-agx-orin"

        return self._check_version("jetpack", current, device_model)


@register_check
class RKNNVersionCheck(AIVersionCheck):
    """Check RKNN SDK version (Rockchip devices)"""

    check_id = "rknn_version"
    title = "RKNN SDK Version"
    description = "Check RKNN SDK version on Rockchip devices"

    def run(self) -> CheckResult:
        # Check if Rockchip device
        is_rockchip = False
        try:
            with open("/proc/device-tree/compatible", "r") as f:
                compat = f.read().lower()
                is_rockchip = "rockchip" in compat or "rk35" in compat
        except Exception as e:
            pass  # TODO: 添加日志

        if not is_rockchip and not self._file_exists("/dev/rknpu"):
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.INFO,
                passed=True,
                title=self.title,
                current="n/a",
                expected="n/a",
                message="Not a Rockchip NPU device",
            )

        # Try Python import
        try:
            from rknn.api import RKNN

            rknn = RKNN()
            current = rknn.get_sdk_version().decode("utf-8").split(" ")[-1]
        except ImportError:
            # Check via file
            output = self._run_command("cat /usr/local/rknpu2/version.txt 2>/dev/null || echo ''")
            if output:
                current = output.strip()
            else:
                return CheckResult(
                    check_id=self.check_id,
                    category=self.category,
                    severity=CheckSeverity.WARNING,
                    passed=True,
                    title=self.title,
                    current="installed",
                    expected="version detectable",
                    message="RKNN SDK installed but version could not be determined",
                )

        return self._check_version("rknn_sdk", current)


@register_check
class PyTorchVersionCheck(AIVersionCheck):
    """Check PyTorch version"""

    check_id = "pytorch_version"
    title = "PyTorch Version"
    description = "Check PyTorch version"

    def run(self) -> CheckResult:
        try:
            import torch

            current = torch.__version__
        except ImportError:
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.WARNING,
                passed=True,
                title=self.title,
                current="not installed",
                expected="installed",
                message="PyTorch not installed",
                fix_available=True,
                fix_command="pip install torch",
                fix_description="Install PyTorch",
                fix_risk="low",
            )

        return self._check_version("pytorch", current)


@register_check
class ONNXRuntimeVersionCheck(AIVersionCheck):
    """Check ONNX Runtime version"""

    check_id = "onnxruntime_version"
    title = "ONNX Runtime Version"
    description = "Check ONNX Runtime version"

    def run(self) -> CheckResult:
        try:
            import onnxruntime as ort

            current = ort.__version__
        except ImportError:
            return CheckResult(
                check_id=self.check_id,
                category=self.category,
                severity=CheckSeverity.INFO,
                passed=True,
                title=self.title,
                current="not installed",
                expected="installed",
                message="ONNX Runtime not installed",
                fix_available=True,
                fix_command="pip install onnxruntime",
                fix_description="Install ONNX Runtime",
                fix_risk="low",
            )

        return self._check_version("onnxruntime", current)


# Backward compat: VersionCheckerCheck -> AIVersionCheck
def __getattr__(name):
    if name == "VersionCheckerCheck":
        return AIVersionCheck
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
