"""
Device profile loader for nastool v3.0

Loads device-specific diagnostic profiles from YAML configuration files.
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# Lazy import yaml to handle missing optional dependency
_yaml = None


def _get_yaml():
    global _yaml
    if _yaml is None:
        try:
            import yaml as _yaml_mod
            _yaml = _yaml_mod
        except ImportError:
            raise ImportError(
                "PyYAML is required for profile loading. Install with: pip install pyyaml"
            )
    return _yaml


class DeviceProfile:
    """Represents a device diagnostic profile."""

    def __init__(self, profile_data: Dict[str, Any]):
        self.data = profile_data
        self.id = list(profile_data.keys())[0] if profile_data else "generic-arm64"
        self.config = profile_data.get(self.id, {})

    @property
    def name(self) -> str:
        return self.config.get("name", "Unknown Device")

    @property
    def vendor(self) -> str:
        return self.config.get("vendor", "Unknown")

    @property
    def category(self) -> str:
        return self.config.get("category", "generic")

    @property
    def checks(self) -> Dict[str, List[str]]:
        return self.config.get("checks", {})

    @property
    def fixes(self) -> List[str]:
        return self.config.get("fixes", [])

    @property
    def thresholds(self) -> Dict[str, Any]:
        return self.config.get("thresholds", {})

    @property
    def benchmarks(self) -> List[str]:
        return self.config.get("benchmarks", [])

    @property
    def cpu(self) -> Dict[str, Any]:
        return self.config.get("cpu", {})

    @property
    def gpu(self) -> Dict[str, Any]:
        return self.config.get("gpu", {})

    @property
    def npu(self) -> Dict[str, Any]:
        return self.config.get("npu", {})

    @property
    def ai(self) -> Dict[str, Any]:
        return self.config.get("ai", {})

    def get_checks_for_category(self, category: str) -> List[str]:
        """Get all checks for a specific category."""
        return self.checks.get(category, [])

    def get_threshold(self, key: str) -> Any:
        """Get a threshold value with fallback to default."""
        return self.thresholds.get(key)

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "vendor": self.vendor,
            "category": self.category,
            "checks": self.checks,
            "fixes": self.fixes,
            "thresholds": self.thresholds,
            "benchmarks": self.benchmarks,
        }


class ProfileLoader:
    """Loads and manages device profiles."""

    # Profile search paths
    PROFILE_DIRS = [
        Path(__file__).parent,  # profiles/
        Path.home() / ".nastool" / "profiles",
        Path("/etc/nastool/profiles"),
    ]

    def __init__(self):
        self._profiles: Dict[str, DeviceProfile] = {}
        self._loaded = False

    def load_all(self) -> None:
        """Load all available device profiles."""
        if self._loaded:
            return

        for profile_dir in self.PROFILE_DIRS:
            if not profile_dir.exists():
                continue

            for yaml_file in profile_dir.glob("*.yaml"):
                self._load_yaml_file(yaml_file)

        self._loaded = True

    def _load_yaml_file(self, filepath: Path) -> None:
        """Load profiles from a YAML file.

        Supports both single-document YAML and multi-document YAML
        (documents separated by ``---``). The first document may be
        a metadata header (contains ``version`` + ``last_updated``)
        which is silently skipped.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                docs = list(_get_yaml().safe_load_all(f))

            for data in docs:
                if not data:
                    continue

                if isinstance(data, dict):
                    # A document may mix metadata keys with profile data.
                    # Strip known metadata keys and treat remaining top-level
                    # keys as device profiles.
                    meta_keys = {"version", "last_updated", "total_new_devices"}
                    profile_keys = [k for k in data.keys() if k not in meta_keys]

                    if not profile_keys:
                        # Pure metadata document, skip
                        continue

                    for pk in profile_keys:
                        sub = {pk: data[pk]}
                        profile = DeviceProfile(sub)
                        self._profiles[profile.id] = profile

        except Exception as e:
            print(f"Warning: Failed to load profile from {filepath}: {e}")

    def get_profile(self, profile_id: str) -> Optional[DeviceProfile]:
        """Get a profile by ID."""
        self.load_all()
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[str]:
        """List all available profile IDs."""
        self.load_all()
        return list(self._profiles.keys())

    def detect_device(self) -> DeviceProfile:
        """
        Auto-detect device and return matching profile.
        Falls back to generic-arm64 if no match found.
        """
        self.load_all()

        # Detection priority: Jetson > RK3588 > Raspberry Pi > QNAP > TerraMaster
        detected_id = self._detect_jetson()
        if detected_id:
            return self._profiles.get(detected_id, self._get_generic())

        detected_id = self._detect_rk3588()
        if detected_id:
            return self._profiles.get(detected_id, self._get_generic())

        detected_id = self._detect_raspberry_pi()
        if detected_id:
            return self._profiles.get(detected_id, self._get_generic())

        detected_id = self._detect_qnap()
        if detected_id:
            return self._profiles.get(detected_id, self._get_generic())

        detected_id = self._detect_terramaster()
        if detected_id:
            return self._profiles.get(detected_id, self._get_generic())

        return self._get_generic()

    # ── Device Detection Methods ─────────────────────────────────

    def _detect_jetson(self) -> Optional[str]:
        """Detect NVIDIA Jetson device via /proc/device-tree/model."""
        try:
            model_file = Path("/proc/device-tree/model")
            if model_file.exists():
                model = model_file.read_text().strip()
                if "Xavier NX" in model:
                    return "jetson-xavier-nx"
                elif "Orin Nano" in model:
                    return "jetson-orin-nano"
                elif "Orin NX" in model:
                    return "jetson-orin-nx"
                elif "TX2" in model:
                    return "jetson-tx2"
                elif "AGX Xavier" in model:
                    return "jetson-agx-xavier"
                elif "AGX Orin" in model:
                    return "jetson-agx-orin"
                elif "Nano" in model:
                    return "jetson-nano"
        except Exception:
            pass

        # Check tegra soc family
        try:
            family_file = Path("/sys/devices/soc0/family")
            if family_file.exists():
                family = family_file.read_text().strip()
                if "tegra" in family.lower():
                    return "jetson-xavier-nx"
        except Exception:
            pass

        return None

    def _detect_rk3588(self) -> Optional[str]:
        """Detect Rockchip RK3588 SBC via device-tree compatible string."""
        try:
            compat_file = Path("/proc/device-tree/compatible")
            if compat_file.exists():
                compat_str = compat_file.read_text().strip()
                if "rk3588" in compat_str:
                    if "orange-pi-5" in compat_str or "orangepi5" in compat_str:
                        return "rk3588-orangepi5"
                    elif "rock-5b" in compat_str:
                        return "rk3588-rock5b"
                    elif "nanopi-r6s" in compat_str:
                        return "rk3588-nanopi-r6s"
                    elif "orangepi-5-plus" in compat_str:
                        return "orangepi-5-plus"
                    elif "rock-5-itx" in compat_str or "rock5itx" in compat_str:
                        return "radxa-rock-5-itx"
                    return "rk3588-orangepi5"  # Generic RK3588 fallback
        except Exception:
            pass

        try:
            machine_file = Path("/sys/devices/soc0/machine")
            if machine_file.exists():
                machine = machine_file.read_text().strip()
                if "RK3588" in machine:
                    return "rk3588-orangepi5"
        except Exception:
            pass

        return None

    def _detect_raspberry_pi(self) -> Optional[str]:
        """Detect Raspberry Pi via device-tree model or cpuinfo."""
        candidates = [
            ("Raspberry Pi 5", "pi5"),
            ("Raspberry Pi 4", "pi4"),
            ("Raspberry Pi 3", "pi3"),
        ]
        try:
            model_file = Path("/proc/device-tree/model")
            if model_file.exists():
                model = model_file.read_text().strip()
                for name, pid in candidates:
                    if name in model:
                        return pid
        except Exception:
            pass

        try:
            cpuinfo = Path("/proc/cpuinfo").read_text()
            for name, pid in candidates:
                if name in cpuinfo:
                    return pid
        except Exception:
            pass

        return None

    def _detect_qnap(self) -> Optional[str]:
        """Detect QNAP NAS via /etc/nas.conf or hostname patterns."""
        # Check QNAP-specific config file
        try:
            nas_conf = Path("/etc/nas.conf")
            if nas_conf.exists():
                content = nas_conf.read_text().strip()
                model_map = {
                    "TS-264": "qnap-ts-264",
                    "TS-464": "qnap-ts-464",
                    "TS-673A": "qnap-ts-673a",
                    "TS-873A": "qnap-ts-873a",
                    "TS-h2490FU": "qnap-ts-h2490fu",
                }
                for name, pid in model_map.items():
                    if name in content:
                        return pid
        except Exception:
            pass

        # Check hostname pattern (QNAP hosts start with TS-)
        try:
            hostname = Path("/proc/sys/kernel/hostname").read_text().strip()
            if hostname.startswith("TS-"):
                # Return generic QNAP x86 profile as fallback
                return "qnap-ts-464"
        except Exception:
            pass

        return None

    def _detect_terramaster(self) -> Optional[str]:
        """Detect TerraMaster NAS via hostname."""
        try:
            hostname = Path("/proc/sys/kernel/hostname").read_text().strip()
            if hostname.startswith("F") and ("-" in hostname):
                # TerraMaster hostname patterns: F4-423, F5-422, etc.
                if "F4-" in hostname:
                    return "terramaster-f4-423"
                elif "F5-" in hostname:
                    return "terramaster-f5-422"
                # Generic TerraMaster fallback
                return "terramaster-f4-423"
        except Exception:
            pass

        return None

    def _get_generic(self) -> DeviceProfile:
        """Get generic ARM64 profile as fallback."""
        self.load_all()
        if "generic-arm64" in self._profiles:
            return self._profiles["generic-arm64"]

        # Create minimal generic profile
        return DeviceProfile(
            {
                "generic-arm64": {
                    "name": "Generic ARM64 Device",
                    "vendor": "Unknown",
                    "category": "generic",
                    "checks": {
                        "system": ["python_version", "pip_installed", "memory_check", "disk_space"],
                        "network": ["internet_access", "dns_resolve", "nas_backend"],
                        "storage": ["storage_disk", "write_speed", "path_exists"],
                        "ai": ["gpu_detected"],
                        "security": ["firewall", "ssh_root"],
                    },
                    "fixes": ["install_python", "config_dns", "create_paths"],
                    "thresholds": {},
                }
            }
        )


# Singleton instance
_loader: Optional[ProfileLoader] = None


def get_loader() -> ProfileLoader:
    """Get the singleton profile loader."""
    global _loader
    if _loader is None:
        _loader = ProfileLoader()
    return _loader


def detect_device() -> DeviceProfile:
    """Auto-detect current device and return profile."""
    return get_loader().detect_device()


def get_profile(profile_id: str) -> Optional[DeviceProfile]:
    """Get a specific profile by ID."""
    return get_loader().get_profile(profile_id)


def list_profiles() -> List[str]:
    """List all available device profiles."""
    return get_loader().list_profiles()
