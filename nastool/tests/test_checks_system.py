"""
test_checks_system.py - Unit tests for system checks

Covers 9 system checks:
- python_version, pip_installed, system_libs, memory, cpu_temp, uptime, docker_containers
"""

import unittest
from checks.base import CheckResult, CheckSeverity, CheckCategory


def make_result(check_id, severity, passed):
    return CheckResult(
        check_id=check_id,
        category=CheckCategory.SYSTEM,
        severity=severity,
        passed=passed,
        title="Test",
        current="current",
        expected="expected",
        message="test message",
    )


class TestPythonVersionCheck(unittest.TestCase):
    """Test PythonVersionCheck exists and has correct interface."""

    def test_python_version_check_registered(self):
        from checks import get_check

        check = get_check("python_version")
        self.assertIsNotNone(check)

    def test_python_version_check_interface(self):
        from checks import get_check

        check = get_check("python_version")
        instance = check()
        self.assertEqual(instance.check_id, "python_version")
        self.assertTrue(hasattr(instance, "run"))
        self.assertTrue(callable(instance.run))


class TestPipInstalledCheck(unittest.TestCase):
    """Test PipInstalledCheck exists."""

    def test_pip_installed_check_registered(self):
        from checks import get_check

        check = get_check("pip_installed")
        self.assertIsNotNone(check)


class TestSystemLibsCheck(unittest.TestCase):
    """Test SystemLibsCheck exists."""

    def test_system_libs_check_registered(self):
        from checks import get_check

        check = get_check("system_libs")
        self.assertIsNotNone(check)


class TestMemoryCheck(unittest.TestCase):
    """Test MemoryCheck exists."""

    def test_memory_check_instance(self):
        from checks import get_check

        check = get_check("memory_check")
        self.assertIsNotNone(check)


class TestCPUTempCheck(unittest.TestCase):
    """Test CPUTempCheck exists."""

    def test_cpu_temp_check_registered(self):
        from checks import get_check

        check = get_check("cpu_temperature")
        self.assertIsNotNone(check)

    def test_cpu_temp_check_interface(self):
        from checks import get_check

        check = get_check("cpu_temperature")
        instance = check()
        self.assertEqual(instance.check_id, "cpu_temperature")
        self.assertTrue(callable(instance.run))


class TestUptimeCheck(unittest.TestCase):
    """Test UptimeCheck exists."""

    def test_system_uptime_check_registered(self):
        from checks import get_check

        check = get_check("system_uptime")
        self.assertIsNotNone(check)


class TestDockerContainersCheck(unittest.TestCase):
    """Test DockerContainersCheck exists."""

    def test_docker_containers_check_registered(self):
        from checks import get_check

        check = get_check("docker_containers")
        self.assertIsNotNone(check)


if __name__ == "__main__":
    unittest.main()
