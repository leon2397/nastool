"""
test_exceptions.py — Unit tests for exceptions module
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exceptions import (
    NastoolError,
    CheckFailedError,
    FixFailedError,
    DeviceNotDetectedError,
    ProfileNotFoundError,
    ConfigurationError,
    NetworkError,
    PermissionError,
    DependencyError,
)


class TestNastoolError(unittest.TestCase):
    def test_is_exception(self):
        self.assertTrue(issubclass(NastoolError, Exception))

    def test_can_raise(self):
        with self.assertRaises(NastoolError):
            raise NastoolError("test error")


class TestCheckFailedError(unittest.TestCase):
    def test_basic_error(self):
        err = CheckFailedError("python_version", "version too old")
        self.assertEqual(err.check_id, "python_version")
        self.assertEqual(err.message, "version too old")

    def test_to_dict(self):
        err = CheckFailedError("disk", "no space")
        d = err.to_dict()
        self.assertEqual(d["check_id"], "disk")
        self.assertEqual(d["message"], "no space")


class TestFixFailedError(unittest.TestCase):
    def test_basic_error(self):
        err = FixFailedError("install_python", "Permission denied")
        self.assertEqual(err.fix_id, "install_python")
        self.assertEqual(err.reason, "Permission denied")

    def test_with_suggestion(self):
        err = FixFailedError("install_python", "Permission denied", "Run as root")
        self.assertEqual(err.suggestion, "Run as root")
        self.assertIn("Permission denied", str(err))

    def test_to_dict(self):
        err = FixFailedError("config_dns", "no network")
        d = err.to_dict()
        self.assertEqual(d["fix_id"], "config_dns")


class TestDeviceNotDetectedError(unittest.TestCase):
    def test_basic_error(self):
        err = DeviceNotDetectedError()
        self.assertIsNotNone(str(err))  # str() returns Chinese message

    def test_with_hints(self):
        hints = {"cpu": "aarch64", "gpu": "unknown"}
        err = DeviceNotDetectedError(hints=hints)
        self.assertEqual(err.hints, hints)

    def test_to_dict(self):
        err = DeviceNotDetectedError()
        d = err.to_dict()
        self.assertIn("error", d)


class TestProfileNotFoundError(unittest.TestCase):
    def test_basic_error(self):
        err = ProfileNotFoundError("unknown-profile")
        self.assertEqual(err.profile_id, "unknown-profile")

    def test_with_available(self):
        available = ["jetson-xavier-nx", "rpi5"]
        err = ProfileNotFoundError("jetson-nano", available=available)
        self.assertEqual(err.available, available)

    def test_to_dict(self):
        err = ProfileNotFoundError("bad-profile")
        d = err.to_dict()
        self.assertEqual(d["profile_id"], "bad-profile")


class TestConfigurationError(unittest.TestCase):
    def test_basic_error(self):
        err = ConfigurationError("yaml_key", "str", "int")
        d = err.to_dict()
        self.assertEqual(d["config_key"], "yaml_key")
        self.assertEqual(d["expected"], "str")

    def test_to_dict(self):
        err = ConfigurationError("missing_key", "str", 123)
        d = err.to_dict()
        self.assertEqual(d["config_key"], "missing_key")


class TestNetworkError(unittest.TestCase):
    def test_basic_error(self):
        err = NetworkError("connect", "192.168.1.100:8000")
        self.assertIn("192.168.1.100", str(err))

    def test_with_original_error(self):
        original = TimeoutError("Connection timed out")
        err = NetworkError("connect", "10.0.0.1", original_error=original)
        self.assertEqual(err.original_error, original)


class TestPermissionError(unittest.TestCase):
    def test_basic_error(self):
        err = PermissionError("install")
        self.assertIn("install", str(err))

    def test_custom_required(self):
        err = PermissionError("install", required="root")
        self.assertEqual(err.required, "root")


class TestDependencyError(unittest.TestCase):
    def test_basic_error(self):
        err = DependencyError("cuda")
        self.assertEqual(err.dependency, "cuda")

    def test_with_install_hint(self):
        err = DependencyError("cuda", "pip install cuda-toolkit")
        self.assertEqual(err.install_hint, "pip install cuda-toolkit")

    def test_to_dict(self):
        err = DependencyError("pytorch")
        d = err.to_dict()
        self.assertEqual(d["dependency"], "pytorch")


class TestExceptionInheritance(unittest.TestCase):
    def test_all_inherit_from_nastool_error(self):
        for cls in [
            CheckFailedError,
            FixFailedError,
            DeviceNotDetectedError,
            ProfileNotFoundError,
            ConfigurationError,
            NetworkError,
            PermissionError,
            DependencyError,
        ]:
            self.assertTrue(issubclass(cls, NastoolError))
