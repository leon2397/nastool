"""
test_profiles_loader.py — Unit tests for device profile loader

Tests:
- YAML loading (devices.yaml + new_devices.yaml = 22 profiles)
- Device profile detection (Jetson/RK3588/Synology/QNAP/TerraMaster)
- Profile format validation (required fields)
- list_profiles() / get_profile() / detect_device() API
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

nastool_root = Path(__file__).parent.parent.resolve()
if str(nastool_root) not in sys.path:
    sys.path.insert(0, str(nastool_root))

from profiles.loader import (
    ProfileLoader,
    DeviceProfile,
    detect_device,
    list_profiles,
    get_profile,
)


class TestDeviceProfileDataclass(unittest.TestCase):
    """Test DeviceProfile data class."""

    def test_profile_creation(self):
        data = {
            "test-device": {
                "name": "Test Device",
                "vendor": "TestCo",
                "arch": "aarch64",
                "chip_type": "arm",
                "ai_type": "cpu",
                "checks": {},
                "fixes": [],
            }
        }
        profile = DeviceProfile(data)
        self.assertEqual(profile.id, "test-device")
        self.assertEqual(profile.name, "Test Device")
        self.assertEqual(profile.vendor, "TestCo")

    def test_profile_defaults(self):
        data = {"minimal-device": {"name": "Minimal"}}
        profile = DeviceProfile(data)
        self.assertEqual(profile.name, "Minimal")
        self.assertEqual(profile.vendor, "Unknown")

    def test_profile_has_checks_property(self):
        data = {"dev": {"name": "D", "checks": {"system": {"cpu": "50"}}}}
        profile = DeviceProfile(data)
        self.assertIsInstance(profile.checks, dict)

    def test_profile_has_fixes_property(self):
        data = {"dev": {"name": "D", "fixes": ["install_python", "install_cuda"]}}
        profile = DeviceProfile(data)
        self.assertIsInstance(profile.fixes, list)
        self.assertEqual(len(profile.fixes), 2)


class TestProfileLoader(unittest.TestCase):
    """Test ProfileLoader class."""

    def test_loader_creation(self):
        loader = ProfileLoader()
        self.assertIsNotNone(loader)

    def test_load_profiles_count(self):
        loader = ProfileLoader()
        profiles = list_profiles()
        # devices.yaml (9) + new_devices.yaml (13) = 22
        self.assertGreaterEqual(len(profiles), 22)

    def test_all_profile_ids_are_strings(self):
        profiles = list_profiles()
        self.assertTrue(all(isinstance(p, str) for p in profiles))

    def test_all_profiles_have_required_properties(self):
        profiles = list_profiles()
        for pid in profiles:
            profile = get_profile(pid)
            self.assertIsNotNone(profile, f"Profile {pid} not found")
            self.assertIsInstance(profile.name, str)
            self.assertIsInstance(profile.vendor, str)
            self.assertIsInstance(profile.checks, dict)


class TestProfileDetection(unittest.TestCase):
    """Test device detection logic."""

    def test_detect_device_returns_device_profile(self):
        profile = detect_device()
        self.assertIsInstance(profile, DeviceProfile)
        self.assertTrue(hasattr(profile, "name"))
        self.assertTrue(hasattr(profile, "vendor"))
        self.assertTrue(hasattr(profile, "id"))

    def test_detect_returns_valid_profile(self):
        profile = detect_device()
        self.assertIsNotNone(profile.id)
        self.assertIsNotNone(profile.name)


class TestListProfiles(unittest.TestCase):
    """Test list_profiles()."""

    def test_list_profiles_returns_list(self):
        profiles = list_profiles()
        self.assertIsInstance(profiles, list)
        self.assertGreaterEqual(len(profiles), 22)

    def test_list_profiles_includes_jetson(self):
        profiles = list_profiles()
        self.assertTrue(any("jetson" in p for p in profiles))

    def test_list_profiles_includes_rk3588(self):
        profiles = list_profiles()
        self.assertTrue(any("rk3588" in p for p in profiles))


class TestGetProfile(unittest.TestCase):
    """Test get_profile()."""

    def test_get_profile_valid_id(self):
        # Get first profile ID
        profiles = list_profiles()
        profile = get_profile(profiles[0])
        self.assertIsNotNone(profile)
        self.assertEqual(profile.id, profiles[0])

    def test_get_profile_invalid_id(self):
        profile = get_profile("nonexistent-device-xyz-12345")
        self.assertIsNone(profile)


class TestNewDevicesCoverage(unittest.TestCase):
    """Test the 13 new devices in new_devices.yaml are loaded."""

    def test_new_devices_loaded(self):
        profiles = list_profiles()

        # Check for QNAP devices (at least some should be present)
        qnap_found = sum(1 for p in profiles if "qnap" in p.lower() or "ts-" in p.lower())
        self.assertGreaterEqual(
            qnap_found, 3, f"Expected ≥3 QNAP devices, got {qnap_found}"
        )

        # Check for ASUS Asustor devices
        asustor_found = sum(1 for p in profiles if "asustor" in p.lower() or "as-" in p.lower())
        self.assertGreaterEqual(
            asustor_found, 2, f"Expected ≥2 ASUS Asustor devices, got {asustor_found}"
        )

        # Check for TerraMaster
        terra_found = sum(1 for p in profiles if "terra" in p.lower() or "f4-" in p.lower())
        self.assertGreaterEqual(
            terra_found, 1, f"Expected ≥1 TerraMaster device, got {terra_found}"
        )

    def test_total_device_count(self):
        profiles = list_profiles()
        self.assertGreaterEqual(len(profiles), 22, f"Got {len(profiles)} profiles")


class TestProfileYAMLFormat(unittest.TestCase):
    """Test YAML files are parseable (handle Python comment workaround)."""

    def test_devices_yaml_loads_via_loader(self):
        # The loader handles Python comments by using safe_load_all
        loader = ProfileLoader()
        profiles = list_profiles()
        self.assertIsInstance(profiles, list)

    def test_new_devices_yaml_loads(self):
        # new_devices.yaml should be clean YAML
        import yaml

        new_yaml = nastool_root / "profiles" / "new_devices.yaml"
        with open(new_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load_all(f)
            docs = list(data)
        self.assertGreaterEqual(len(docs), 10, "new_devices.yaml should have ≥10 profiles")


if __name__ == "__main__":
    unittest.main()
