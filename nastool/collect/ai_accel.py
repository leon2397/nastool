"""
core/ai_accel.py — AI 加速设备自动识别 + 推理能力检测

这是 nastool 的差异化模块：多数 NAS 检测工具只看硬盘和网络，
这里把「这台机器能不能跑本地 AI」也量化出来（相册分类 / 人脸 / 转码都会用到）。

支持：
  NVIDIA    → nvidia-smi / Jetson /dev/nvidia0 / CUDA
  AMD       → /dev/kfd / rocm-smi
  Rockchip  → /dev/rknpu / RKNN SDK
  华为昇腾   → CANN / /dev/davinci*
  Intel     → /dev/dri/renderD128 / /dev/intel-npu / Movidius
  算能 TPU   → /dev/sophon*
  Google    → Coral Edge TPU /dev/apex_*
  CPU       → PyTorch / ONNX Runtime / NumPy 兜底

重要：AI 能力在本工具里是「加分项」，不是合格必要条件。
     一台不跑 AI 的纯文件 NAS 也应该判为健康。
"""
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional

from .util import IS_LINUX, read_file, run, safe_listdir


class ChipType:
    NONE = "none"
    NVIDIA_GPU = "nvidia_gpu"
    AMD_GPU = "amd_gpu"
    ROCKCHIP_NPU = "rockchip_npu"
    HUAWEI_ASCEND = "huawei_ascend"
    INTEL_NPU = "intel_npu"
    SOPHGO_TPU = "sophgo_tpu"
    GOOGLE_TPU = "google_tpu"
    QUALCOMM_QNN = "qualcomm_qnn"
    CPU = "cpu"


@dataclass
class AcceleratorDevice:
    name: str = ""
    chip_type: str = ChipType.NONE
    vendor: str = ""
    memory_total_mb: int = 0
    memory_available_mb: int = 0
    tflops_fp16: float = 0.0
    detected_by: str = ""
    driver_version: str = ""
    runtime_version: str = ""
    available: bool = False


@dataclass
class AIFacts:
    devices: List[AcceleratorDevice] = field(default_factory=list)
    primary: Optional[AcceleratorDevice] = None
    best_chip_type: str = ChipType.NONE
    hardware_accelerated: bool = False   # 是否检测到真实加速硬件
    inference_available: bool = False
    inference_engine: str = ""
    inference_test_passed: bool = False
    inference_test_ms: float = 0.0
    config_path: str = ""                # 配置文件里 npu_type 的提示（可选）
    config_npu_type: str = ""
    inference_tested: bool = True        # 是否真的跑了推理测试
    notes: List[str] = field(default_factory=list)   # 纯信息说明，不参与判定


def _dev_entries() -> list:
    return safe_listdir("/dev")


def _detect_nvidia() -> List[AcceleratorDevice]:
    devs: List[AcceleratorDevice] = []
    out = run("nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version,"
              "compute_cap --format=csv,noheader 2>/dev/null", timeout=8)
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        dev = AcceleratorDevice(
            name=parts[0], chip_type=ChipType.NVIDIA_GPU, vendor="NVIDIA",
            driver_version=parts[3] if len(parts) > 3 else "",
            detected_by="nvidia-smi", available=True,
        )
        for idx, attr in ((1, "memory_total_mb"), (2, "memory_available_mb")):
            if len(parts) > idx:
                digits = "".join(ch for ch in parts[idx] if ch.isdigit())
                if digits:
                    setattr(dev, attr, int(digits))
        if len(parts) > 4:
            try:
                dev.tflops_fp16 = round(float(parts[4]) * 2000, 1)
            except ValueError:
                pass
        devs.append(dev)

    if os.path.exists("/dev/nvidia0") and not devs:
        dev = AcceleratorDevice(
            name="NVIDIA Jetson (GPU)", chip_type=ChipType.NVIDIA_GPU, vendor="NVIDIA",
            detected_by="/dev/nvidia0", available=True,
        )
        model = read_file("/proc/device-tree/model").rstrip("\x00")
        if model:
            dev.name = f"NVIDIA {model}"
        devs.append(dev)

    if devs:
        nvbuf = run("nvbuf_version 2>/dev/null", timeout=5)
        if nvbuf:
            for d in devs:
                if not d.runtime_version:
                    d.runtime_version = nvbuf
    return devs


def _detect_amd() -> List[AcceleratorDevice]:
    devs: List[AcceleratorDevice] = []
    if os.path.exists("/dev/kfd") or os.path.exists("/dev/dri/renderD128"):
        smi = run("rocm-smi --showproductname --showdriverversion 2>/dev/null", timeout=8)
        if smi or os.path.exists("/dev/kfd"):
            name = "AMD GPU (ROCm)"
            for line in smi.splitlines():
                if "Card series" in line or "Card model" in line:
                    name = line.split(":", 1)[-1].strip() or name
                    break
            devs.append(AcceleratorDevice(
                name=name, chip_type=ChipType.AMD_GPU, vendor="AMD",
                detected_by="/dev/kfd" if os.path.exists("/dev/kfd") else "/dev/dri/renderD128",
                runtime_version="ROCm" if smi else "", available=True,
            ))
    return devs


def _detect_rockchip() -> List[AcceleratorDevice]:
    devs: List[AcceleratorDevice] = []
    if os.path.exists("/dev/rknpu"):
        dev = AcceleratorDevice(
            name="Rockchip NPU", chip_type=ChipType.ROCKCHIP_NPU, vendor="Rockchip",
            detected_by="/dev/rknpu", available=True,
        )
        fw = run("cat /sys/class/npu/npu/firmware_version 2>/dev/null", timeout=5)
        if fw:
            dev.runtime_version = fw
        for path in ("/usr/local/rknpu2/rknn_rknn_api/librknn_api.so",
                     "/usr/lib/librknnrt.so",
                     "/usr/local/rknpu/rknn_api/librknn_api.so"):
            if os.path.exists(path):
                dev.detected_by = path
                break
        model = read_file("/proc/device-tree/model").rstrip("\x00")
        if model:
            dev.name = f"Rockchip NPU ({model})"
        devs.append(dev)
    return devs


def _detect_huawei_ascend() -> List[AcceleratorDevice]:
    devs: List[AcceleratorDevice] = []
    if os.path.exists("/usr/local/Ascend"):
        cann = run("cat /usr/local/Ascend/latest/version.cfg 2>/dev/null | grep -i version", timeout=5)
        devs.append(AcceleratorDevice(
            name="Huawei Ascend NPU", chip_type=ChipType.HUAWEI_ASCEND, vendor="Huawei",
            runtime_version=cann or "CANN", detected_by="/usr/local/Ascend", available=True,
        ))
    else:
        for entry in _dev_entries():
            if entry.startswith("davinci"):
                devs.append(AcceleratorDevice(
                    name=f"Huawei Ascend ({entry})", chip_type=ChipType.HUAWEI_ASCEND,
                    vendor="Huawei", detected_by=f"/dev/{entry}",
                    available=os.access(f"/dev/{entry}", os.R_OK),
                ))
                break
    return devs


def _detect_intel() -> List[AcceleratorDevice]:
    devs: List[AcceleratorDevice] = []
    if os.path.exists("/dev/dri/renderD128"):
        info = run("vainfo 2>/dev/null | grep -i 'driver version'", timeout=6)
        devs.append(AcceleratorDevice(
            name="Intel Integrated GPU", chip_type=ChipType.INTEL_NPU, vendor="Intel",
            driver_version=info or "i915", detected_by="/dev/dri/renderD128", available=True,
        ))
    if os.path.exists("/dev/intel-npu"):
        devs.append(AcceleratorDevice(
            name="Intel NPU", chip_type=ChipType.INTEL_NPU, vendor="Intel",
            detected_by="/dev/intel-npu", available=True,
        ))
    for entry in _dev_entries():
        if entry.startswith("myriad"):
            devs.append(AcceleratorDevice(
                name=f"Intel Movidius ({entry})", chip_type=ChipType.INTEL_NPU,
                vendor="Intel", detected_by=f"/dev/{entry}",
                available=os.access(f"/dev/{entry}", os.R_OK),
            ))
            break
    return devs


def _detect_sophgo() -> List[AcceleratorDevice]:
    for entry in _dev_entries():
        if entry.startswith("sophon") or entry.startswith("bm"):
            dev = AcceleratorDevice(
                name=f"Sophgo TPU ({entry})", chip_type=ChipType.SOPHGO_TPU,
                vendor="Sophgo", detected_by=f"/dev/{entry}",
                available=os.access(f"/dev/{entry}", os.R_OK),
            )
            name = read_file("/sys/class/misc/sophon0/device/name")
            if name:
                dev.name = name
            return [dev]
    return []


def _detect_google_tpu() -> List[AcceleratorDevice]:
    for entry in _dev_entries():
        if entry.startswith("apex"):
            return [AcceleratorDevice(
                name=f"Google Coral Edge TPU ({entry})", chip_type=ChipType.GOOGLE_TPU,
                vendor="Google", detected_by=f"/dev/{entry}", available=True,
            )]
    return []


def _detect_cpu_fallback() -> AcceleratorDevice:
    import platform
    cpu_name = run("lscpu 2>/dev/null | grep -i 'model name' | cut -d: -f2", timeout=5)
    return AcceleratorDevice(
        name=cpu_name.strip() or f"CPU ({platform.machine()})",
        chip_type=ChipType.CPU, vendor="CPU", detected_by="cpu", available=True,
    )


def _run_inference_test(device: AcceleratorDevice) -> tuple:
    """
    真实跑一次轻量推理，返回 (success, elapsed_ms, engine)。
    用当前 Python 解释器，避免测试结果和实际运行环境不一致。
    """
    import time

    py = sys.executable or "python3"
    snippets = [
        ("PyTorch", "import torch;x=torch.randn(1,3,64,64);"
                    "m=torch.nn.Conv2d(3,16,3);m(x);print('ok')", 30),
        ("ONNXRuntime", "import onnxruntime as ort;"
                        "print('ok' if ort.get_available_providers() else 'ok')", 20),
        ("NumPy", "import numpy as np;x=np.random.randn(256,256);"
                  "np.dot(x,x);print('ok')", 15),
    ]
    for engine, code, timeout in snippets:
        start = time.time()
        out = run(f'"{py}" -c "{code}" 2>/dev/null', timeout=timeout)
        if "ok" in out:
            return True, round((time.time() - start) * 1000, 1), engine
    return False, 0.0, ""


def _load_config_hint() -> tuple:
    """
    可选：从配置文件里读期望的 npu_type，和实际检测结果做对照。
    只找通用位置，不绑定任何特定产品。
    """
    candidates = []
    env_cfg = os.environ.get("NASTOOL_CONFIG", "")
    if env_cfg:
        candidates.append(env_cfg)
    candidates += [
        "./config.yaml", "./config.yml",
        "/etc/nastool/config.yaml",
        os.path.expanduser("~/.config/nastool/config.yaml"),
    ]
    for path in candidates:
        if not path or not os.path.exists(path):
            continue
        try:
            import yaml  # 可选依赖
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = yaml.safe_load(f) or {}
            for section in ("device", "Device"):
                if isinstance(data.get(section), dict):
                    npu = data[section].get("npu_type", "")
                    if npu:
                        return path, str(npu)
            if isinstance(data.get("npu_type"), str) and data["npu_type"]:
                return path, data["npu_type"]
        except Exception:  # noqa: BLE001 - yaml 缺失或格式错都跳过
            continue
    return "", ""


def detect_ai_accelerator(do_inference_test: bool = True) -> AIFacts:
    """
    主入口：探测所有 AI 加速设备 + 推理测试。
    优先级：NVIDIA > AMD > Rockchip > 昇腾 > Intel > Sophgo > Google > CPU
    """
    report = AIFacts()
    report.config_path, report.config_npu_type = _load_config_hint()

    detectors = [
        _detect_nvidia, _detect_amd, _detect_rockchip,
        _detect_huawei_ascend, _detect_intel, _detect_sophgo, _detect_google_tpu,
    ]
    devices: List[AcceleratorDevice] = []
    for detector in detectors:
        try:
            devices.extend(detector())
        except Exception:  # noqa: BLE001
            continue

    hardware = [d for d in devices if d.chip_type != ChipType.CPU]
    report.hardware_accelerated = bool(hardware)

    if not devices:
        devices.append(_detect_cpu_fallback())
    report.devices = devices

    primary = next((d for d in devices if d.available and d.chip_type != ChipType.CPU), None)
    primary = primary or devices[0]
    report.primary = primary
    report.best_chip_type = primary.chip_type

    if do_inference_test:
        success, elapsed, engine = _run_inference_test(primary)
        report.inference_available = success
        report.inference_engine = engine
        report.inference_test_passed = success
        report.inference_test_ms = elapsed
    else:
        report.inference_tested = False


    return report
