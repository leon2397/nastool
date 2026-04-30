# -*- coding: utf-8 -*-
"""GPU/NPU 检测 (declarative style)

改进版本 (v4.1):
- 多源数据验证：文件设备、驱动信息、命令输出
- 驱动状态检测：读取GPU驱动版本和状态
- 设备类型适配：支持多种GPU/NPU类型
- 数据融合：综合多种检测结果
"""

from __future__ import annotations

import platform
import subprocess
import re
import os
from typing import Dict, List, Optional, Any

from nastool_core.checks.decorators import check, CheckContext
from nastool_core.checks.base import CheckCategory, CheckSeverity, CheckResult, DataSourceInfo


GPU_DEVICES = {
    "/dev/nvidia0": {"Name": "NVIDIA GPU", "type": "nvidia_gpu", "driver_cmd": "nvidia-smi"},
    "/dev/nvidia": {"Name": "NVIDIA GPU", "type": "nvidia_gpu", "driver_cmd": "nvidia-smi"},
    "/dev/rknpu": {"Name": "Rockchip NPU", "type": "rockchip_npu", "driver_cmd": "rkaiq"},
    "/dev/davinci0": {"Name": "Huawei Ascend NPU", "type": "huawei_ascend", "driver_cmd": "ascend-toolkit"},
    "/dev/davinci": {"Name": "Huawei Ascend NPU", "type": "huawei_ascend", "driver_cmd": "ascend-toolkit"},
    "/dev/intel-npu": {"Name": "Intel NPU", "type": "intel_npu", "driver_cmd": "igpu-clk"},
    "/dev/dri/renderD128": {"Name": "GPU (DRI)", "type": "dri_gpu", "driver_cmd": "glxinfo"},
}


def _collect_gpu_info_multi_source() -> tuple:
    """
    Collect GPU info from multiple sources.

    Returns:
        Tuple of (detected list, sources_info list)
    """
    detected = []
    sources_info = []

    for device_path, info in GPU_DEVICES.items():
        source_info = DataSourceInfo(
            name=info["Name"],
            source_type="device_file",
            available=False,
            priority=100
        )

        if os.path.exists(device_path):
            source_info.available = True
            source_info.last_value = {"path": device_path, "type": info["type"]}
            detected.append({
                "path": device_path,
                "Name": info["Name"],
                "type": info["type"],
                "source": "device_file"
            })

        sources_info.append(source_info)

    driver_info = _detect_gpu_driver()
    if driver_info:
        source_info = DataSourceInfo(
            name="GPU Driver",
            source_type="driver_command",
            available=True,
            priority=50,
            last_value=driver_info
        )
        sources_info.append(source_info)

        for driver in driver_info:
            detected.append({
                "path": driver.get("path", ""),
                "Name": driver.get("Name", "Unknown"),
                "type": driver.get("type", "unknown"),
                "driver_version": driver.get("version", ""),
                "source": "driver_command"
            })

    lspci_info = _detect_via_lspci()
    if lspci_info:
        source_info = DataSourceInfo(
            name="PCI Device",
            source_type="lspci",
            available=True,
            priority=80,
            last_value=lspci_info
        )
        sources_info.append(source_info)

        for device in lspci_info:
            if not any(d.get("path") == device.get("path") for d in detected):
                detected.append({
                    "path": device.get("path", ""),
                    "Name": device.get("Name", "Unknown"),
                    "type": device.get("type", "unknown"),
                    "source": "lspci"
                })

    jetson_info = _detect_jetson()
    if jetson_info:
        source_info = DataSourceInfo(
            name="Jetson Device",
            source_type="device_tree",
            available=True,
            priority=30,
            last_value=jetson_info
        )
        sources_info.append(source_info)

        if not any(d.get("type") == "nvidia_jetson" for d in detected):
            detected.append({
                "path": "/proc/device-tree/model",
                "Name": jetson_info.get("model", "Jetson"),
                "type": "nvidia_jetson",
                "jetpack": jetson_info.get("jetpack", ""),
                "source": "device_tree"
            })

    if platform.system() == "Darwin" and platform.machine() == "arm64":
        source_info = DataSourceInfo(
            name="Apple Silicon",
            source_type="platform_info",
            available=True,
            priority=20,
            last_value={"type": "apple_silicon"}
        )
        sources_info.append(source_info)

        detected.append({
            "path": "sysctl",
            "Name": "Apple Silicon",
            "type": "apple_silicon",
            "source": "platform_info"
        })

    return detected, sources_info


def _detect_gpu_driver() -> List[Dict[str, Any]]:
    """Detect GPU driver information"""
    drivers = []

    nvidia_smi = _check_nvidia_smi()
    if nvidia_smi:
        drivers.append(nvidia_smi)

    if os.path.exists("/dev/rknpu"):
        rknpu_info = _check_rknpu_driver()
        if rknpu_info:
            drivers.append(rknpu_info)

    if os.path.exists("/dev/davinci0") or os.path.exists("/dev/davinci"):
        ascend_info = _check_ascend_driver()
        if ascend_info:
            drivers.append(ascend_info)

    return drivers


def _check_nvidia_smi() -> Optional[Dict[str, Any]]:
    """Check NVIDIA GPU via nvidia-smi"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            line = result.stdout.strip().split(",")
            if len(line) >= 3:
                return {
                    "name": "NVIDIA GPU",
                    "type": "nvidia_gpu",
                    "version": line[1].strip(),
                    "memory": line[2].strip(),
                    "path": "/dev/nvidia0"
                }
            elif len(line) >= 1:
                return {
                    "name": line[0].strip(),
                    "type": "nvidia_gpu",
                    "path": "/dev/nvidia0"
                }
    except Exception:
        pass
    return None


def _check_rknpu_driver() -> Optional[Dict[str, Any]]:
    """Check Rockchip NPU driver"""
    try:
        if os.path.exists("/sys/class/npu"):
            for npu in os.listdir("/sys/class/npu"):
                npu_path = os.path.join("/sys/class/npu", npu)
                version_file = os.path.join(npu_path, "version")
                if os.path.exists(version_file):
                    with open(version_file) as f:
                        version = f.read().strip()
                    return {
                        "name": "Rockchip NPU",
                        "type": "rockchip_npu",
                        "version": version,
                        "path": "/dev/rknpu"
                    }
    except Exception:
        pass
    return None


def _check_ascend_driver() -> Optional[Dict[str, Any]]:
    """Check Huawei Ascend driver"""
    try:
        version_file = "/usr/local/Ascend/ascend-toolkit/latest/version.cfg"
        if os.path.exists(version_file):
            with open(version_file) as f:
                content = f.read()
                match = re.search(r"version\s*=\s*(.+)", content)
                if match:
                    return {
                        "name": "Huawei Ascend NPU",
                        "type": "huawei_ascend",
                        "version": match.group(1).strip(),
                        "path": "/dev/davinci0"
                    }
    except Exception:
        pass
    return None


def _detect_via_lspci() -> List[Dict[str, Any]]:
    """Detect GPU via lspci"""
    detected = []

    try:
        result = subprocess.run(
            ["lspci"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line_lower = line.lower()
                if "vga" in line_lower or "display" in line_lower or "3d" in line_lower:
                    match = re.search(r"([0-9a-f:.]+)\s+(.+)", line)
                    if match:
                        pci_addr = match.group(1)
                        desc = match.group(2).strip()

                        gpu_type = "unknown"
                        if "nvidia" in line_lower:
                            gpu_type = "nvidia_gpu"
                        elif "amd" in line_lower or "radeon" in line_lower:
                            gpu_type = "amd_gpu"
                        elif "intel" in line_lower:
                            gpu_type = "intel_gpu"

                        detected.append({
                            "path": f"/sys/bus/pci/devices/{pci_addr}",
                            "name": desc,
                            "type": gpu_type,
                            "pci_addr": pci_addr
                        })
    except Exception:
        pass

    return detected


def _detect_jetson() -> Optional[Dict[str, Any]]:
    """Detect Jetson device"""
    try:
        model_file = "/proc/device-tree/model"
        if os.path.exists(model_file):
            with open(model_file, "r") as f:
                model = f.read().strip()

            if "jetson" in model.lower():
                jetpack = ""
                try:
                    result = subprocess.run(
                        ["dpkg", "-l", "nvidia-jetpack"],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        match = re.search(r"nvidia-jetpack\s+(\S+)", result.stdout)
                        if match:
                            jetpack = match.group(1)
                except Exception:
                    pass

                return {
                    "model": model,
                    "jetpack": jetpack,
                    "type": "nvidia_jetson"
                }
    except Exception:
        pass
    return None


@check(
    id="gpu_detected",
    category=CheckCategory.AI,
    severity=CheckSeverity.WARNING,
    title="GPU/NPU Detection",
    description="Check if AI accelerator is detected",
    timeout=10,
)
def gpu_detected(ctx: CheckContext) -> CheckResult:
    """Detect GPU/NPU with multi-source validation"""
    detected, sources_info = _collect_gpu_info_multi_source()

    if detected:
        unique_types = list(set(d.get("type", "unknown") for d in detected))
        names = [d.get("name", "Unknown") for d in detected]
        unique_names = list(set(names))

        driver_versions = []
        for d in detected:
            if "driver_version" in d:
                driver_versions.append(d["driver_version"])

        details = {
            "detected": detected,
            "types": unique_types,
            "count": len(detected),
            "data_sources": [
                {"name": s.name, "available": s.available, "type": s.source_type}
                for s in sources_info
            ]
        }

        if driver_versions:
            details["driver_versions"] = driver_versions

        message = f"AI accelerator detected: {', '.join(unique_names)}"
        if len(unique_types) > 1:
            message += f" ({len(unique_types)} types)"
        if driver_versions:
            message += f", Driver: {', '.join(driver_versions)}"

        return ctx.passed(
            current="detected",
            expected="detected",
            message=message,
            details=details,
        )

    return ctx.warning(
        current="none",
        expected="detected",
        message="No AI accelerator detected, will use CPU fallback",
        fix_available=True,
        fix_description="Install GPU/NPU drivers",
    )


GPUDetectedCheck = gpu_detected
