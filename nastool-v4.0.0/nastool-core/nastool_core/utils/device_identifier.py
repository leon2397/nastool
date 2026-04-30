"""
Device Identifier for NASTool

Provides device identification and type detection for ARM devices.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum
import platform
import os


class DeviceType(Enum):
    """Device type enumeration"""
    RK3588 = "rk3588"
    RK3568 = "rk3568"
    RK3399 = "rk3399"
    JETSON_XAVIER = "jetson_xavier"
    JETSON_NANO = "jetson_nano"
    JETSON_ORIN = "jetson_orin"
    ASCEND_310 = "ascend_310"
    ASCEND_910 = "ascend_910"
    SOPHON = "sophon"
    GENERIC_ARM = "generic_arm"
    X86 = "x86"
    UNKNOWN = "unknown"


class DeviceCategory(Enum):
    """Device category"""
    NAS = "nas"
    AI_SERVER = "ai_server"
    EDGE_COMPUTING = "edge_computing"
    DEVELOPMENT = "development"
    GENERIC = "generic"


@dataclass
class DeviceInfo:
    """Device information"""
    device_id: str
    device_type: DeviceType
    device_name: str
    manufacturer: str
    category: DeviceCategory
    chip_model: str
    cpu_info: Dict[str, Any] = field(default_factory=dict)
    memory_info: Dict[str, Any] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)
    detection_method: str = ""
    confidence: float = 1.0
    raw_data: Dict[str, Any] = field(default_factory=dict)


class DeviceIdentifier:
    """
    Device identifier for detecting device type and characteristics.

    Supports identification of:
    - Rockchip RK series (RK3588, RK3568, RK3399)
    - NVIDIA Jetson series (Xavier, Nano, Orin)
    - Huawei Ascend series
    - Sophon AI accelerators
    - Generic ARM devices
    """

    DEVICE_PATTERNS = {
        DeviceType.RK3588: {
            "device_tree": ["rk3588", "rockchip,rk3588"],
            "cpu_model": ["rk3588", "rockchip,rk3588"],
            "soc_id": ["3588"],
        },
        DeviceType.RK3568: {
            "device_tree": ["rk3568", "rockchip,rk3568"],
            "cpu_model": ["rk3568", "rockchip,rk3568"],
            "soc_id": ["3568"],
        },
        DeviceType.RK3399: {
            "device_tree": ["rk3399", "rockchip,rk3399"],
            "cpu_model": ["rk3399", "rockchip,rk3399"],
            "soc_id": ["3399"],
        },
        DeviceType.JETSON_XAVIER: {
            "device_tree": ["jetson-xavier", "p2972-0000"],
            "cpu_model": ["tegra194", "carmel"],
        },
        DeviceType.JETSON_NANO: {
            "device_tree": ["jetson-nano", "p3448-0000"],
            "cpu_model": ["tegra210", "cortex-a57"],
        },
        DeviceType.JETSON_ORIN: {
            "device_tree": ["jetson-orin", "p3701-0000"],
            "cpu_model": ["tegra234", "carmel"],
        },
        DeviceType.ASCEND_310: {
            "device_tree": ["ascend-310"],
            "cpu_model": ["ascend 310"],
        },
        DeviceType.ASCEND_910: {
            "device_tree": ["ascend-910"],
            "cpu_model": ["ascend 910"],
        },
    }

    DEVICE_FEATURES = {
        DeviceType.RK3588: ["npu", "gpu", "usb3", "pcie", "nvme"],
        DeviceType.RK3568: ["npu", "gpu", "usb3", "pcie"],
        DeviceType.RK3399: ["gpu", "usb3", "pcie"],
        DeviceType.JETSON_XAVIER: ["npu", "gpu", "usb3", "pcie", "nvme", "camera"],
        DeviceType.JETSON_NANO: ["gpu", "usb3", "camera"],
        DeviceType.JETSON_ORIN: ["npu", "gpu", "usb3", "pcie", "nvme", "camera"],
        DeviceType.ASCEND_310: ["npu"],
        DeviceType.ASCEND_910: ["npu"],
    }

    def __init__(self):
        self._device_info: Optional[DeviceInfo] = None

    def identify(self) -> DeviceInfo:
        """
        Identify the current device.

        Returns:
            DeviceInfo object
        """
        if self._device_info is not None:
            return self._device_info

        device_type = self._detect_device_type()
        device_name = self._detect_device_name(device_type)
        manufacturer = self._detect_manufacturer(device_type)
        category = self._detect_category(device_type)
        chip_model = self._detect_chip_model(device_type)
        cpu_info = self._get_cpu_info()
        memory_info = self._get_memory_info()
        features = self.DEVICE_FEATURES.get(device_type, [])

        self._device_info = DeviceInfo(
            device_id=self._generate_device_id(device_type, chip_model),
            device_type=device_type,
            device_name=device_name,
            manufacturer=manufacturer,
            category=category,
            chip_model=chip_model,
            cpu_info=cpu_info,
            memory_info=memory_info,
            features=features,
            detection_method="auto",
            confidence=self._calculate_confidence(device_type)
        )

        return self._device_info

    def _detect_device_type(self) -> DeviceType:
        """Detect device type from various sources"""
        if platform.system() == "Windows":
            return DeviceType.X86

        if platform.system() == "Darwin":
            return DeviceType.GENERIC_ARM

        detection_order = [
            self._check_device_tree,
            self._check_cpuinfo,
            self._check_soc_id,
            self._check_sysfs,
            self._check_command_output,
        ]

        for detection_method in detection_order:
            device_type = detection_method()
            if device_type != DeviceType.UNKNOWN:
                return device_type

        return DeviceType.UNKNOWN

    def _check_device_tree(self) -> DeviceType:
        """Check device tree model"""
        model_paths = [
            "/proc/device-tree/model",
            "/proc/device-tree/compatible",
        ]

        for path in model_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        content = f.read().lower()
                        for device_type, patterns in self.DEVICE_PATTERNS.items():
                            for pattern in patterns.get("device_tree", []):
                                if pattern in content:
                                    return device_type
            except Exception:
                pass

        return DeviceType.UNKNOWN

    def _check_cpuinfo(self) -> DeviceType:
        """Check /proc/cpuinfo"""
        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", 'r') as f:
                    content = f.read().lower()
                    for device_type, patterns in self.DEVICE_PATTERNS.items():
                        for pattern in patterns.get("cpu_model", []):
                            if pattern in content:
                                return device_type
        except Exception:
            pass

        return DeviceType.UNKNOWN

    def _check_soc_id(self) -> DeviceType:
        """Check SOC ID"""
        soc_id_paths = [
            "/sys/class/socinfo/soc_id",
            "/sys/devices/soc0/soc_id",
        ]

        try:
            for path in soc_id_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        content = f.read().lower()
                        for device_type, patterns in self.DEVICE_PATTERNS.items():
                            for pattern in patterns.get("soc_id", []):
                                if pattern in content:
                                    return device_type
        except Exception:
            pass

        return DeviceType.UNKNOWN

    def _check_sysfs(self) -> DeviceType:
        """Check sysfs for device info"""
        try:
            hw_rev_path = "/sys/class/socinfo/hw_rev"
            if os.path.exists(hw_rev_path):
                return DeviceType.RK3588
        except Exception:
            pass

        return DeviceType.UNKNOWN

    def _check_command_output(self) -> DeviceType:
        """Check command output for device identification"""
        commands = [
            ("cat /proc/device-tree/model 2>/dev/null", ""),
            ("cat /sys/firmware/devicetree/base/model 2>/dev/null", ""),
        ]

        for cmd, _ in commands:
            try:
                import subprocess
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    content = result.stdout.lower()
                    for device_type, patterns in self.DEVICE_PATTERNS.items():
                        for pattern in patterns.get("device_tree", []):
                            if pattern in content:
                                return device_type
            except Exception:
                pass

        return DeviceType.UNKNOWN

    def _detect_device_name(self, device_type: DeviceType) -> str:
        """Get human-readable device name"""
        names = {
            DeviceType.RK3588: "Rockchip RK3588 Development Board",
            DeviceType.RK3568: "Rockchip RK3568 Development Board",
            DeviceType.RK3399: "Rockchip RK3399 Development Board",
            DeviceType.JETSON_XAVIER: "NVIDIA Jetson Xavier NX",
            DeviceType.JETSON_NANO: "NVIDIA Jetson Nano",
            DeviceType.JETSON_ORIN: "NVIDIA Jetson AGX Orin",
            DeviceType.ASCEND_310: "Huawei Ascend 310 AI Processor",
            DeviceType.ASCEND_910: "Huawei Ascend 910 AI Processor",
            DeviceType.SOPHON: "Sophon AI Accelerator",
            DeviceType.GENERIC_ARM: "Generic ARM Device",
            DeviceType.X86: "x86/x64 Device",
            DeviceType.UNKNOWN: "Unknown Device",
        }
        return names.get(device_type, "Unknown Device")

    def _detect_manufacturer(self, device_type: DeviceType) -> str:
        """Detect device manufacturer"""
        manufacturers = {
            DeviceType.RK3588: "Rockchip",
            DeviceType.RK3568: "Rockchip",
            DeviceType.RK3399: "Rockchip",
            DeviceType.JETSON_XAVIER: "NVIDIA",
            DeviceType.JETSON_NANO: "NVIDIA",
            DeviceType.JETSON_ORIN: "NVIDIA",
            DeviceType.ASCEND_310: "Huawei",
            DeviceType.ASCEND_910: "Huawei",
            DeviceType.SOPHON: "Sophon",
            DeviceType.GENERIC_ARM: "Unknown",
            DeviceType.X86: "Generic",
            DeviceType.UNKNOWN: "Unknown",
        }
        return manufacturers.get(device_type, "Unknown")

    def _detect_category(self, device_type: DeviceType) -> DeviceCategory:
        """Detect device category"""
        if device_type in [DeviceType.JETSON_XAVIER, DeviceType.JETSON_NANO, DeviceType.JETSON_ORIN]:
            return DeviceCategory.AI_SERVER
        elif device_type in [DeviceType.ASCEND_310, DeviceType.ASCEND_910, DeviceType.SOPHON]:
            return DeviceCategory.AI_SERVER
        elif device_type in [DeviceType.RK3588, DeviceType.RK3568, DeviceType.RK3399]:
            return DeviceCategory.EDGE_COMPUTING
        else:
            return DeviceCategory.GENERIC

    def _detect_chip_model(self, device_type: DeviceType) -> str:
        """Detect chip model string"""
        chip_models = {
            DeviceType.RK3588: "RK3588",
            DeviceType.RK3568: "RK3568",
            DeviceType.RK3399: "RK3399",
            DeviceType.JETSON_XAVIER: "tegra194",
            DeviceType.JETSON_NANO: "tegra210",
            DeviceType.JETSON_ORIN: "tegra234",
            DeviceType.ASCEND_310: "Ascend 310",
            DeviceType.ASCEND_910: "Ascend 910",
            DeviceType.SOPHON: "BM1684",
            DeviceType.GENERIC_ARM: "ARM",
            DeviceType.X86: platform.machine(),
            DeviceType.UNKNOWN: "Unknown",
        }
        return chip_models.get(device_type, "Unknown")

    def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information"""
        cpu_info = {
            "processor": "Unknown",
            "model_name": "Unknown",
            "core_count": 0,
            "architecture": platform.machine(),
        }

        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    for line in lines:
                        if line.startswith("processor"):
                            cpu_info["core_count"] += 1
                        elif line.startswith("model name"):
                            cpu_info["model_name"] = line.split(':')[1].strip()
                        elif "Hardware" in line:
                            cpu_info["processor"] = line.split(':')[1].strip()
        except Exception:
            pass

        return cpu_info

    def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory information"""
        memory_info = {
            "total_mb": 0,
            "swap_mb": 0,
        }

        try:
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", 'r') as f:
                    for line in f:
                        if line.startswith("MemTotal"):
                            kb = int(line.split()[1])
                            memory_info["total_mb"] = kb // 1024
                        elif line.startswith("SwapTotal"):
                            kb = int(line.split()[1])
                            memory_info["swap_mb"] = kb // 1024
        except Exception:
            pass

        return memory_info

    def _generate_device_id(self, device_type: DeviceType, chip_model: str) -> str:
        """Generate unique device ID"""
        return f"{device_type.value}_{chip_model.lower()}"

    def _calculate_confidence(self, device_type: DeviceType) -> float:
        """Calculate detection confidence"""
        if device_type == DeviceType.UNKNOWN:
            return 0.0
        elif device_type in [DeviceType.X86, DeviceType.GENERIC_ARM]:
            return 0.9
        else:
            return 0.95

    def get_device_type(self) -> DeviceType:
        """Get device type (convenience method)"""
        return self.identify().device_type

    def get_device_name(self) -> str:
        """Get device name (convenience method)"""
        return self.identify().device_name

    def get_features(self) -> List[str]:
        """Get device features (convenience method)"""
        return self.identify().features


_global_identifier: Optional[DeviceIdentifier] = None


def get_device_identifier() -> DeviceIdentifier:
    """Get global device identifier instance"""
    global _global_identifier
    if _global_identifier is None:
        _global_identifier = DeviceIdentifier()
    return _global_identifier


def identify_device() -> DeviceInfo:
    """Identify current device (convenience function)"""
    return get_device_identifier().identify()
