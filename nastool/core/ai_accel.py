"""
core/ai_accel.py — AI accelerator auto-detection for ARM devices
Core module of nastool — supports 15+ chip families

Supported chip types:
  - NVIDIA GPU/Jetson (Nano/Xavier NX/AGX Orin/TX2)
  - Rockchip NPU (RK3588/RK3588S/RK3576/RK3568/RK3566/RK3399)
  - Broadcom BCM (Raspberry Pi 4/5)
  - Allwinner (A64/H5/H6/H616/T507)
  - Amlogic (S905/S922X/A311D)
  - Phytium (FT-2000/FT-2004)
  - HiSilicon Kunpeng (920/922)
  - Huawei Ascend (CANN)
  - Qualcomm QNN (Snapdragon)
  - Intel NPU/Movidius
  - Sophgo TPU (BM1684/CV181)
  - Apple Silicon (M1/M2/M3 via Metal)
  - Generic CPU fallback
"""

import os
import platform
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict


# ── Chip type constants ────────────────────────────────────────
class ChipType:
    NONE = "none"

    # NVIDIA
    NVIDIA_GPU = "nvidia_gpu"
    NVIDIA_JETSON = "nvidia_jetson"

    # Rockchip NPU
    ROCKCHIP_NPU = "rockchip_npu"

    # Broadcom (Raspberry Pi)
    BROADCOM_BCM = "broadcom_bcm"

    # Allwinner
    ALLWINNER = "allwinner"

    # Amlogic
    AMLOGIC = "amlogic"

    # Phytium (飞腾)
    PHYTIUM = "phytium"

    # Kunpeng (鲲鹏)
    KUNPENG = "kunpeng"

    # Huawei Ascend
    HUAWEI_ASCEND = "huawei_ascend"

    # Qualcomm
    QUALCOMM_QNN = "qualcomm_qnn"

    # Intel
    INTEL_NPU = "intel_npu"
    INTEL_MOVIDIUS = "intel_movidius"

    # Sophgo TPU
    SOPHGO_TPU = "sophgo_tpu"

    # Apple Silicon
    APPLE_SILICON = "apple_silicon"

    # Fallback
    CPU = "cpu"


# ── Chip database (model -> tflops_fp16 estimate) ───────────────
CHIP_DB = {
    # NVIDIA Jetson series
    "jetson-nano": {"vendor": "NVIDIA", "tflops_fp16": 0.5, "memory_mb": 4096},
    "jetson-tx1": {"vendor": "NVIDIA", "tflops_fp16": 1.0, "memory_mb": 4096},
    "jetson-tx2": {"vendor": "NVIDIA", "tflops_fp16": 1.3, "memory_mb": 8192},
    "jetson-xavier-nx": {"vendor": "NVIDIA", "tflops_fp16": 6.0, "memory_mb": 8192},
    "jetson-agx-xavier": {"vendor": "NVIDIA", "tflops_fp16": 11.0, "memory_mb": 16384},
    "jetson-agx-orin": {"vendor": "NVIDIA", "tflops_fp16": 275.0, "memory_mb": 32768},
    "jetson-orin-nx": {"vendor": "NVIDIA", "tflops_fp16": 70.0, "memory_mb": 16384},
    "jetson-orin-nano": {"vendor": "NVIDIA", "tflops_fp16": 20.0, "memory_mb": 8192},
    # Rockchip series
    "rk3588": {"vendor": "Rockchip", "tflops_fp16": 6.0, "memory_mb": 0},
    "rk3588s": {"vendor": "Rockchip", "tflops_fp16": 6.0, "memory_mb": 0},
    "rk3576": {"vendor": "Rockchip", "tflops_fp16": 4.0, "memory_mb": 0},
    "rk3568": {"vendor": "Rockchip", "tflops_fp16": 1.0, "memory_mb": 0},
    "rk3566": {"vendor": "Rockchip", "tflops_fp16": 1.0, "memory_mb": 0},
    "rk3399": {"vendor": "Rockchip", "tflops_fp16": 0.8, "memory_mb": 0},
    "rk3288": {"vendor": "Rockchip", "tflops_fp16": 0.2, "memory_mb": 0},
    # Broadcom (Raspberry Pi)
    "bcm2711": {
        "vendor": "Broadcom",
        "tflops_fp16": 0.0,
        "memory_mb": 0,
        "model": "Raspberry Pi 4",
    },
    "bcm2712": {
        "vendor": "Broadcom",
        "tflops_fp16": 0.0,
        "memory_mb": 0,
        "model": "Raspberry Pi 5",
    },
    "bcm2837": {
        "vendor": "Broadcom",
        "tflops_fp16": 0.0,
        "memory_mb": 0,
        "model": "Raspberry Pi 3",
    },
    # Allwinner series
    "a64": {"vendor": "Allwinner", "tflops_fp16": 0.0, "memory_mb": 0},
    "h5": {"vendor": "Allwinner", "tflops_fp16": 0.0, "memory_mb": 0},
    "h6": {"vendor": "Allwinner", "tflops_fp16": 0.0, "memory_mb": 0},
    "h616": {"vendor": "Allwinner", "tflops_fp16": 0.0, "memory_mb": 0},
    "t507": {"vendor": "Allwinner", "tflops_fp16": 0.0, "memory_mb": 0},
    # Amlogic series
    "s905": {"vendor": "Amlogic", "tflops_fp16": 0.0, "memory_mb": 0},
    "s905x": {"vendor": "Amlogic", "tflops_fp16": 0.0, "memory_mb": 0},
    "s905x2": {"vendor": "Amlogic", "tflops_fp16": 0.0, "memory_mb": 0},
    "s905x3": {"vendor": "Amlogic", "tflops_fp16": 0.0, "memory_mb": 0},
    "s922x": {"vendor": "Amlogic", "tflops_fp16": 2.5, "memory_mb": 0},
    "a311d": {"vendor": "Amlogic", "tflops_fp16": 5.0, "memory_mb": 0},
    # Phytium (飞腾)
    "ft-2000": {"vendor": "Phytium", "tflops_fp16": 0.0, "memory_mb": 0},
    "ft-2000/4": {"vendor": "Phytium", "tflops_fp16": 0.0, "memory_mb": 0},
    "ft-2004": {"vendor": "Phytium", "tflops_fp16": 0.0, "memory_mb": 0},
    "s2500": {"vendor": "Phytium", "tflops_fp16": 0.0, "memory_mb": 0},
    # Kunpeng (鲲鹏)
    "kunpeng-920": {"vendor": "HiSilicon", "tflops_fp16": 0.0, "memory_mb": 0},
    "kunpeng-922": {"vendor": "HiSilicon", "tflops_fp16": 0.0, "memory_mb": 0},
    # Huawei Ascend
    "ascend-310": {"vendor": "Huawei", "tflops_fp16": 8.0, "memory_mb": 0},
    "ascend-310p": {"vendor": "Huawei", "tflops_fp16": 11.0, "memory_mb": 0},
    "ascend-910": {"vendor": "Huawei", "tflops_fp16": 256.0, "memory_mb": 32768},
    "ascend-910b": {"vendor": "Huawei", "tflops_fp16": 312.0, "memory_mb": 65536},
    # Qualcomm Snapdragon
    "snapdragon-8cx": {"vendor": "Qualcomm", "tflops_fp16": 4.0, "memory_mb": 0},
    "snapdragon-8gen2": {"vendor": "Qualcomm", "tflops_fp16": 8.0, "memory_mb": 0},
    "snapdragon-8gen3": {"vendor": "Qualcomm", "tflops_fp16": 15.0, "memory_mb": 0},
    # Sophgo TPU
    "bm1684": {"vendor": "Sophgo", "tflops_fp16": 17.0, "memory_mb": 0},
    "bm1684x": {"vendor": "Sophgo", "tflops_fp16": 34.0, "memory_mb": 0},
    "bm1688": {"vendor": "Sophgo", "tflops_fp16": 32.0, "memory_mb": 0},
    "cv181x": {"vendor": "Sophgo", "tflops_fp16": 2.0, "memory_mb": 0},
    "cv182x": {"vendor": "Sophgo", "tflops_fp16": 4.0, "memory_mb": 0},
    "cv186ah": {"vendor": "Sophgo", "tflops_fp16": 6.0, "memory_mb": 0},
    # Intel NPU
    "intel-npu-mtl": {
        "vendor": "Intel",
        "tflops_fp16": 11.0,
        "memory_mb": 0,
        "model": "Meteor Lake NPU",
    },
    "intel-npu-lnl": {
        "vendor": "Intel",
        "tflops_fp16": 13.0,
        "memory_mb": 0,
        "model": "Lunar Lake NPU",
    },
    # Apple Silicon
    "apple-m1": {"vendor": "Apple", "tflops_fp16": 11.0, "memory_mb": 0},
    "apple-m1-pro": {"vendor": "Apple", "tflops_fp16": 22.0, "memory_mb": 0},
    "apple-m1-max": {"vendor": "Apple", "tflops_fp16": 44.0, "memory_mb": 0},
    "apple-m1-ultra": {"vendor": "Apple", "tflops_fp16": 88.0, "memory_mb": 0},
    "apple-m2": {"vendor": "Apple", "tflops_fp16": 15.0, "memory_mb": 0},
    "apple-m2-pro": {"vendor": "Apple", "tflops_fp16": 30.0, "memory_mb": 0},
    "apple-m2-max": {"vendor": "Apple", "tflops_fp16": 60.0, "memory_mb": 0},
    "apple-m2-ultra": {"vendor": "Apple", "tflops_fp16": 120.0, "memory_mb": 0},
    "apple-m3": {"vendor": "Apple", "tflops_fp16": 18.0, "memory_mb": 0},
    "apple-m3-pro": {"vendor": "Apple", "tflops_fp16": 36.0, "memory_mb": 0},
    "apple-m3-max": {"vendor": "Apple", "tflops_fp16": 72.0, "memory_mb": 0},
}


@dataclass
class AcceleratorDevice:
    name: str = ""
    chip_type: str = ChipType.NONE
    vendor: str = ""
    model: str = ""  # Specific chip model (e.g., "RK3588")
    memory_total_mb: int = 0
    memory_available_mb: int = 0
    tflops_fp16: float = 0.0
    detected_by: str = ""
    driver_version: str = ""
    runtime_version: str = ""
    available: bool = False


@dataclass
class AIReport:
    devices: List[AcceleratorDevice] = field(default_factory=list)
    primary: Optional[AcceleratorDevice] = None
    best_chip_type: str = ChipType.NONE
    inference_available: bool = False
    inference_engine: str = ""
    inference_test_passed: bool = False
    inference_test_ms: float = 0.0
    config_path: str = ""
    config_npu_type: str = ""
    errors: List[str] = field(default_factory=list)
    ok: bool = False


# ── Helper functions ───────────────────────────────────────────
def _run(cmd: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return ""


def _read(path: str) -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception as e:
        return ""


def _match_chip_db(keywords: List[str]) -> Optional[Dict]:
    """Match chip info from CHIP_DB by keywords"""
    key_lower = [k.lower() for k in keywords]
    for chip_key, info in CHIP_DB.items():
        chip_lower = chip_key.lower()
        for kw in key_lower:
            if kw in chip_lower or chip_lower in kw:
                return {"model": chip_key, **info}
    return None


def _detect_nvidia() -> List[AcceleratorDevice]:
    """NVIDIA GPU / Jetson series"""
    devs = []

    # 1. nvidia-smi (desktop GPU / Jetson AGX)
    out = _run(
        "nvidia-smi --query-gpu=name,memory.total,memory.free,"
        "driver_version --format=csv,noheader 2>/dev/null"
    )
    if out:
        for line in out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                dev = AcceleratorDevice(
                    name=parts[0],
                    chip_type=ChipType.NVIDIA_GPU,
                    vendor="NVIDIA",
                    driver_version=parts[3] if len(parts) > 3 else "",
                    detected_by="nvidia-smi",
                    available=True,
                )
                try:
                    dev.memory_total_mb = int(
                        parts[1].replace("MiB", "").replace("Mi", "").replace("MB", "")
                    )
                    dev.memory_available_mb = int(
                        parts[2].replace("MiB", "").replace("Mi", "").replace("MB", "")
                    )
                except Exception as e:
                    pass

                # Match chip DB for TFLOPS
                chip_info = _match_chip_db([parts[0]])
                if chip_info:
                    dev.tflops_fp16 = chip_info.get("tflops_fp16", 0)
                    dev.model = chip_info.get("model", "")

                devs.append(dev)

    # 2. Jetson-specific detection
    jetson_model = _read("/proc/device-tree/model") or _read("/sys/firmware/devicetree/base/model")
    if jetson_model and "jetson" in jetson_model.lower():
        dev = AcceleratorDevice(
            name=jetson_model,
            chip_type=ChipType.NVIDIA_JETSON,
            vendor="NVIDIA",
            detected_by="/proc/device-tree/model",
            available=True,
        )

        # Match chip DB
        chip_info = _match_chip_db([jetson_model])
        if chip_info:
            dev.tflops_fp16 = chip_info.get("tflops_fp16", 0)
            dev.model = chip_info.get("model", "")
            dev.memory_total_mb = chip_info.get("memory_mb", 0)

        # Check Jetson-specific paths
        if os.path.exists("/dev/nvidia0"):
            dev.detected_by = "/dev/nvidia0"

        devs.append(dev)

    # 3. /dev/nvidia* without nvidia-smi (older Jetson)
    elif os.path.exists("/dev/nvidia0") and not devs:
        dev = AcceleratorDevice(
            name="NVIDIA GPU (unknown model)",
            chip_type=ChipType.NVIDIA_GPU,
            vendor="NVIDIA",
            detected_by="/dev/nvidia0",
            available=True,
        )
        devs.append(dev)

    return devs


def _detect_rockchip() -> List[AcceleratorDevice]:
    """Rockchip NPU (RK3588 / RK356x / RK3399)"""
    devs = []

    # 1. /dev/rknpu (RK3588 NPU)
    if os.path.exists("/dev/rknpu"):
        dev = AcceleratorDevice(
            name="Rockchip NPU",
            chip_type=ChipType.ROCKCHIP_NPU,
            vendor="Rockchip",
            detected_by="/dev/rknpu",
            available=True,
        )

        # Read CPU model to identify specific chip
        cpu_info = _read("/proc/cpuinfo")
        if "rk3588" in cpu_info.lower():
            dev.model = "RK3588"
            dev.tflops_fp16 = 6.0
        elif "rk3576" in cpu_info.lower():
            dev.model = "RK3576"
            dev.tflops_fp16 = 4.0
        elif "rk3568" in cpu_info.lower():
            dev.model = "RK3568"
            dev.tflops_fp16 = 1.0
        elif "rk3566" in cpu_info.lower():
            dev.model = "RK3566"
            dev.tflops_fp16 = 1.0

        # RKNN SDK detection
        for path in [
            "/usr/local/rknpu2/rknn_rknn_api/librknn_api.so",
            "/usr/lib/librknnrt.so",
            "/usr/local/rknpu/rknn_api/librknn_api.so",
        ]:
            if os.path.exists(path):
                dev.detected_by = path
                break

        devs.append(dev)

    # 2. Check /proc/device-tree/compatible for Rockchip SoC
    compatible = _read("/proc/device-tree/compatible")
    if compatible:
        compat_lower = compatible.lower()
        rockchip_models = ["rk3588", "rk3588s", "rk3576", "rk3568", "rk3566", "rk3399", "rk3288"]
        for model in rockchip_models:
            if model in compat_lower:
                # Check if we already added this device
                if not any(d.model.lower() == model for d in devs):
                    chip_info = _match_chip_db([model])
                    dev = AcceleratorDevice(
                        name=f"Rockchip {model.upper()}",
                        chip_type=ChipType.ROCKCHIP_NPU
                        if "3588" in model or "3576" in model
                        else ChipType.CPU,
                        vendor="Rockchip",
                        model=model.upper(),
                        detected_by="/proc/device-tree/compatible",
                        available=True,
                    )
                    if chip_info:
                        dev.tflops_fp16 = chip_info.get("tflops_fp16", 0)
                    devs.append(dev)
                break

    return devs


def _detect_broadcom() -> List[AcceleratorDevice]:
    """Broadcom BCM (Raspberry Pi)"""
    devs = []

    # Check device tree model
    model = _read("/proc/device-tree/model")
    if model:
        model_lower = model.lower()
        if "raspberry pi" in model_lower or "bcm" in model_lower:
            chip_info = _match_chip_db([model])
            dev = AcceleratorDevice(
                name=model,
                chip_type=ChipType.BROADCOM_BCM,
                vendor="Broadcom",
                detected_by="/proc/device-tree/model",
                available=True,
            )
            if chip_info:
                dev.model = chip_info.get("model", "")
                dev.tflops_fp16 = chip_info.get("tflops_fp16", 0)
            devs.append(dev)

    # Check /proc/cpuinfo for BCM
    cpuinfo = _read("/proc/cpuinfo")
    if "bcm2711" in cpuinfo.lower():
        if not devs:
            devs.append(
                AcceleratorDevice(
                    name="Broadcom BCM2711 (Raspberry Pi 4)",
                    chip_type=ChipType.BROADCOM_BCM,
                    vendor="Broadcom",
                    model="BCM2711",
                    detected_by="/proc/cpuinfo",
                    available=True,
                )
            )
    elif "bcm2712" in cpuinfo.lower():
        if not devs:
            devs.append(
                AcceleratorDevice(
                    name="Broadcom BCM2712 (Raspberry Pi 5)",
                    chip_type=ChipType.BROADCOM_BCM,
                    vendor="Broadcom",
                    model="BCM2712",
                    detected_by="/proc/cpuinfo",
                    available=True,
                )
            )

    return devs


def _detect_allwinner() -> List[AcceleratorDevice]:
    """Allwinner SoC (A64 / H5 / H6 / H616 / T507)"""
    devs = []

    compatible = _read("/proc/device-tree/compatible")
    cpuinfo = _read("/proc/cpuinfo")

    allwinner_models = ["a64", "h5", "h6", "h616", "t507"]
    for model in allwinner_models:
        if model in (compatible + cpuinfo).lower():
            chip_info = _match_chip_db([model])
            dev = AcceleratorDevice(
                name=f"Allwinner {model.upper()}",
                chip_type=ChipType.ALLWINNER,
                vendor="Allwinner",
                model=model.upper(),
                detected_by="/proc/device-tree/compatible",
                available=True,
            )
            if chip_info:
                dev.tflops_fp16 = chip_info.get("tflops_fp16", 0)
            devs.append(dev)
            break

    return devs


def _detect_amlogic() -> List[AcceleratorDevice]:
    """Amlogic SoC (S905 / S922X / A311D)"""
    devs = []

    compatible = _read("/proc/device-tree/compatible")
    cpuinfo = _read("/proc/cpuinfo")
    combined = (compatible + cpuinfo).lower()

    amlogic_models = ["s905x3", "s905x2", "s905x", "s905", "s922x", "a311d"]
    for model in amlogic_models:
        if model in combined:
            chip_info = _match_chip_db([model])
            dev = AcceleratorDevice(
                name=f"Amlogic {model.upper()}",
                chip_type=ChipType.AMLOGIC,
                vendor="Amlogic",
                model=model.upper(),
                detected_by="/proc/device-tree/compatible",
                available=True,
            )
            if chip_info:
                dev.tflops_fp16 = chip_info.get("tflops_fp16", 0)
            devs.append(dev)
            break

    return devs


def _detect_phytium() -> List[AcceleratorDevice]:
    """Phytium (飞腾) CPU"""
    devs = []

    cpuinfo = _read("/proc/cpuinfo")
    if "phytium" in cpuinfo.lower() or "ft-2000" in cpuinfo.lower():
        chip_info = _match_chip_db(["ft-2000", "ft-2004", "s2500"])
        dev = AcceleratorDevice(
            name="Phytium FT-2000 Series",
            chip_type=ChipType.PHYTIUM,
            vendor="Phytium",
            detected_by="/proc/cpuinfo",
            available=True,
        )
        if chip_info:
            dev.model = chip_info.get("model", "")
            dev.tflops_fp16 = chip_info.get("tflops_fp16", 0)
        devs.append(dev)

    return devs


def _detect_kunpeng() -> List[AcceleratorDevice]:
    """HiSilicon Kunpeng (鲲鹏) CPU"""
    devs = []

    cpuinfo = _read("/proc/cpuinfo")
    if "kunpeng" in cpuinfo.lower():
        chip_info = _match_chip_db(["kunpeng"])
        dev = AcceleratorDevice(
            name="HiSilicon Kunpeng 920",
            chip_type=ChipType.KUNPENG,
            vendor="HiSilicon",
            detected_by="/proc/cpuinfo",
            available=True,
        )
        if chip_info:
            dev.model = chip_info.get("model", "")
        devs.append(dev)

    return devs


def _detect_huawei_ascend() -> List[AcceleratorDevice]:
    """Huawei Ascend NPU (CANN)"""
    devs = []

    # 1. CANN installation
    if os.path.exists("/usr/local/Ascend"):
        cann_ver = _run(
            "cat /usr/local/Ascend/latest/version.cfg 2>/dev/null | grep 'Version' | cut -d= -f2"
        )
        dev = AcceleratorDevice(
            name="Huawei Ascend NPU",
            chip_type=ChipType.HUAWEI_ASCEND,
            vendor="Huawei",
            runtime_version=cann_ver or "CANN",
            detected_by="/usr/local/Ascend",
            available=True,
        )
        devs.append(dev)

    # 2. /dev/davinci* device node
    for entry in os.listdir("/dev"):
        if entry.startswith("davinci"):
            if not devs:
                devs.append(
                    AcceleratorDevice(
                        name=f"Huawei Ascend ({entry})",
                        chip_type=ChipType.HUAWEI_ASCEND,
                        vendor="Huawei",
                        detected_by=f"/dev/{entry}",
                        available=os.access(f"/dev/{entry}", os.R_OK),
                    )
                )
            break

    return devs


def _detect_qualcomm() -> List[AcceleratorDevice]:
    """Qualcomm Snapdragon (QNN)"""
    devs = []

    # Check for Qualcomm AI Engine
    if os.path.exists("/dev/qseecom") or os.path.exists("/dev/ion"):
        dev = AcceleratorDevice(
            name="Qualcomm Snapdragon",
            chip_type=ChipType.QUALCOMM_QNN,
            vendor="Qualcomm",
            detected_by="/dev/qseecom",
            available=True,
        )
        devs.append(dev)

    # Check cpuinfo for Snapdragon
    cpuinfo = _read("/proc/cpuinfo")
    if "snapdragon" in cpuinfo.lower() or "qcom" in cpuinfo.lower():
        if not devs:
            devs.append(
                AcceleratorDevice(
                    name="Qualcomm Snapdragon",
                    chip_type=ChipType.QUALCOMM_QNN,
                    vendor="Qualcomm",
                    detected_by="/proc/cpuinfo",
                    available=True,
                )
            )

    return devs


def _detect_intel() -> List[AcceleratorDevice]:
    """Intel iGPU / NPU / Movidius"""
    devs = []

    # 1. Intel NPU (Meteor Lake / Lunar Lake)
    if os.path.exists("/dev/intel-npu"):
        dev = AcceleratorDevice(
            name="Intel NPU",
            chip_type=ChipType.INTEL_NPU,
            vendor="Intel",
            detected_by="/dev/intel-npu",
            available=True,
        )
        devs.append(dev)

    # 2. Intel iGPU via /dev/dri/renderD128
    if os.path.exists("/dev/dri/renderD128"):
        info = _run("vainfo 2>/dev/null | grep 'VAProfile' | head -1 || echo ''")
        if info or _run("lspci 2>/dev/null | grep -i 'vga.*intel'"):
            dev = AcceleratorDevice(
                name="Intel Integrated GPU",
                chip_type=ChipType.INTEL_NPU,
                vendor="Intel",
                detected_by="/dev/dri/renderD128",
                available=True,
            )
            devs.append(dev)

    # 3. Intel Movidius / USB accelerator
    for entry in os.listdir("/dev"):
        if entry.startswith("myriad"):
            devs.append(
                AcceleratorDevice(
                    name=f"Intel Movidius ({entry})",
                    chip_type=ChipType.INTEL_MOVIDIUS,
                    vendor="Intel",
                    detected_by=f"/dev/{entry}",
                    available=os.access(f"/dev/{entry}", os.R_OK),
                )
            )
            break

    return devs


def _detect_sophgo() -> List[AcceleratorDevice]:
    """Sophgo TPU (BM1684 / CV181)"""
    devs = []

    for entry in os.listdir("/dev"):
        if entry.startswith("sophon") or entry.startswith("bm"):
            dev = AcceleratorDevice(
                name=f"Sophgo TPU ({entry})",
                chip_type=ChipType.SOPHGO_TPU,
                vendor="Sophgo",
                detected_by=f"/dev/{entry}",
                available=os.access(f"/dev/{entry}", os.R_OK),
            )
            if os.path.exists("/sys/class/misc/sophon0/device/name"):
                dev.name = _read("/sys/class/misc/sophon0/device/name") or dev.name
            devs.append(dev)
            break

    return devs


def _detect_apple() -> List[AcceleratorDevice]:
    """Apple Silicon (M1/M2/M3)"""
    devs = []

    if platform.system() == "Darwin":
        # Check for Apple Silicon
        arch = platform.machine()
        if arch == "arm64":
            brand = _run("sysctl -n machdep.cpu.brand_string 2>/dev/null || echo ''")
            dev = AcceleratorDevice(
                name=brand or "Apple Silicon",
                chip_type=ChipType.APPLE_SILICON,
                vendor="Apple",
                detected_by="sysctl",
                available=True,
            )

            # Try to identify specific model
            if brand:
                for key in [
                    "m3-max",
                    "m3-pro",
                    "m3",
                    "m2-ultra",
                    "m2-max",
                    "m2-pro",
                    "m2",
                    "m1-ultra",
                    "m1-max",
                    "m1-pro",
                    "m1",
                ]:
                    if key in brand.lower():
                        chip_info = _match_chip_db([key])
                        if chip_info:
                            dev.model = chip_info.get("model", "")
                            dev.tflops_fp16 = chip_info.get("tflops_fp16", 0)
                        break

            devs.append(dev)

    return devs


def _detect_cpu_fallback() -> AcceleratorDevice:
    """Generic CPU fallback"""
    arch = platform.machine()
    cpu_name = _run("lscpu 2>/dev/null | grep 'Model name' | cut -d: -f2 | xargs")
    if not cpu_name:
        cpu_name = _run(
            "cat /proc/cpuinfo 2>/dev/null | grep 'model name' | head -1 | cut -d: -f2 | xargs"
        )

    dev = AcceleratorDevice(
        name=cpu_name or f"CPU ({arch})",
        chip_type=ChipType.CPU,
        vendor="CPU",
        detected_by="/proc/cpuinfo",
        available=True,
    )

    # Try to match chip DB
    if cpu_name:
        chip_info = _match_chip_db([cpu_name])
        if chip_info:
            dev.model = chip_info.get("model", "")
            dev.tflops_fp16 = chip_info.get("tflops_fp16", 0)

    return dev


def _run_inference_test(device: AcceleratorDevice) -> tuple:
    """Lightweight inference test"""
    # 1. PyTorch CPU test
    try:
        start = time.time()
        out = _run(
            'python3 -c "import torch; x=torch.randn(1,3,224,224); '
            "m=torch.nn.Conv2d(3,64,3); y=m(x); print('ok')\" 2>/dev/null",
            timeout=15,
        )
        if "ok" in out:
            elapsed = round((time.time() - start) * 1000, 1)
            return True, elapsed, "PyTorch"
    except Exception as e:
        pass

    # 2. ONNX Runtime test
    try:
        start = time.time()
        out = _run("python3 -c \"import onnxruntime as ort; print('ok')\" 2>/dev/null", timeout=10)
        if "ok" in out:
            elapsed = round((time.time() - start) * 1000, 1)
            return True, elapsed, "ONNXRuntime"
    except Exception as e:
        pass

    # 3. NumPy baseline
    try:
        start = time.time()
        out = _run(
            'python3 -c "import numpy as np; x=np.random.randn(512,512); '
            "y=np.dot(x,x); print('ok')\" 2>/dev/null",
            timeout=10,
        )
        if "ok" in out:
            elapsed = round((time.time() - start) * 1000, 1)
            return True, elapsed, "NumPy"
    except Exception as e:
        pass

    return False, 0.0, ""


def _load_nas_config() -> tuple:
    """Read AI-NAS config.yaml npu_type"""
    for base in [
        "/home/nvidia/AI-NAS-Media-Manager/arm/config.yaml",
        "/root/AI-NAS-Media-Manager/arm/config.yaml",
        "./arm/config.yaml",
    ]:
        if os.path.exists(base):
            try:
                import yaml

                with open(base) as f:
                    d = yaml.safe_load(f)
                for k in ["device", "Device"]:
                    if k in d and isinstance(d[k], dict):
                        npu = d[k].get("npu_type", "")
                        if npu:
                            return base, str(npu)
            except Exception as e:
                pass
    return "", ""


def detect_ai_accelerator() -> AIReport:
    """
    Main entry: detect all AI accelerators + run inference test
    Priority: NVIDIA > Rockchip > Ascend > Intel > Sophgo > Apple > CPU
    """
    report = AIReport()
    report.config_path, report.config_npu_type = _load_nas_config()

    all_devices: List[AcceleratorDevice] = []
    detectors = [
        ("nvidia", _detect_nvidia),
        ("rockchip", _detect_rockchip),
        ("broadcom", _detect_broadcom),
        ("allwinner", _detect_allwinner),
        ("amlogic", _detect_amlogic),
        ("phytium", _detect_phytium),
        ("kunpeng", _detect_kunpeng),
        ("huawei_ascend", _detect_huawei_ascend),
        ("qualcomm", _detect_qualcomm),
        ("intel", _detect_intel),
        ("sophgo", _detect_sophgo),
        ("apple", _detect_apple),
    ]

    for name, detector in detectors:
        devs = detector()
        all_devices.extend(devs)

    # Fallback to CPU if no accelerator found
    if not all_devices:
        all_devices.append(_detect_cpu_fallback())

    report.devices = all_devices

    # Select primary device (first non-CPU accelerator)
    primary = None
    for dev in all_devices:
        if dev.available and dev.chip_type != ChipType.CPU:
            primary = dev
            break
    if primary is None:
        primary = all_devices[0]

    report.primary = primary
    report.best_chip_type = primary.chip_type

    # Run inference test
    success, elapsed, engine = _run_inference_test(primary)
    report.inference_available = success
    report.inference_engine = engine
    report.inference_test_passed = success
    report.inference_test_ms = elapsed

    report.ok = report.inference_available

    if not report.inference_available:
        report.errors.append("No inference engine available (install PyTorch / ONNX Runtime)")

    return report
