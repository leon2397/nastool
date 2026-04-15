"""
test_checks.py — Unit tests for checks module
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from checks import (
    Check,
    CheckResult,
    CheckSeverity,
    CheckCategory,
    CheckSummary,
    run_check,
    get_check,
    list_checks,
    run_all_checks,
)


class TestCheckResult(unittest.TestCase):
    """Test CheckResult dataclass"""

    def test_passed_result(self):
        result = CheckResult(
            check_id="test_check",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.PASSED,
            passed=True,
            title="Test Check",
            current="expected_value",
            expected="expected_value",
            message="All good",
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.severity, CheckSeverity.PASSED)

    def test_failed_result(self):
        result = CheckResult(
            check_id="test_check",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.CRITICAL,
            passed=False,
            title="Test Check",
            current="bad_value",
            expected="good_value",
            message="Value is wrong",
            fix_available=True,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.severity, CheckSeverity.CRITICAL)
        self.assertTrue(result.fix_available)


class TestCheckRegistry(unittest.TestCase):
    """Test check registry functions"""

    def test_list_checks(self):
        checks = list_checks()
        self.assertIsInstance(checks, dict)
        self.assertGreater(len(checks), 0)
        self.assertIn("python_version", checks)
        self.assertIn("internet_access", checks)
        self.assertIn("disk_space", checks)

    def test_get_check(self):
        check_cls = get_check("python_version")
        self.assertIsNotNone(check_cls)
        # Returns a class, not an instance
        self.assertTrue(callable(check_cls))

    def test_get_nonexistent_check(self):
        check_cls = get_check("nonexistent_check_id")
        self.assertIsNone(check_cls)


class TestRunCheck(unittest.TestCase):
    """Test run_check function"""

    def test_run_python_version_check(self):
        result = run_check("python_version")
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "python_version")

    def test_run_nonexistent_check(self):
        result = run_check("nonexistent_check_id")
        self.assertIsNone(result)


class TestInternetAccessCheck(unittest.TestCase):
    """Test InternetAccessCheck"""

    def test_check_attributes(self):
        check_cls = get_check("internet_access")
        self.assertIsNotNone(check_cls)
        instance = check_cls()
        self.assertEqual(instance.check_id, "internet_access")
        self.assertEqual(instance.category, CheckCategory.NETWORK)

    @patch("socket.socket.connect_ex", return_value=0)
    def test_check_passes_when_reachable(self, mock_connect):
        from checks.network.internet_access import InternetAccessCheck

        check = InternetAccessCheck()
        result = check.run()
        self.assertTrue(result.passed)

    @patch("socket.socket.connect_ex", return_value=1)
    def test_check_fails_when_unreachable(self, mock_connect):
        from checks.network.internet_access import InternetAccessCheck

        check = InternetAccessCheck()
        result = check.run()
        self.assertFalse(result.passed)


class TestDNSResolveCheck(unittest.TestCase):
    """Test DNSResolveCheck"""

    def test_check_attributes(self):
        from checks.network.dns_resolve import DNSResolveCheck

        check = DNSResolveCheck()
        self.assertEqual(check.check_id, "dns_resolve")
        self.assertEqual(check.category, CheckCategory.NETWORK)

    @patch("socket.gethostbyname")
    def test_check_passes(self, mock_gethostbyname):
        mock_gethostbyname.return_value = "8.8.8.8"
        from checks.network.dns_resolve import DNSResolveCheck

        check = DNSResolveCheck()
        result = check.run()
        self.assertTrue(result.passed)

    @patch("socket.gethostbyname")
    def test_check_fails_on_gaierror(self, mock_gethostbyname):
        import socket

        mock_gethostbyname.side_effect = socket.gaierror("Name resolution failed")
        from checks.network.dns_resolve import DNSResolveCheck

        check = DNSResolveCheck()
        result = check.run()
        self.assertFalse(result.passed)


class TestCheckSeverity(unittest.TestCase):
    """Test CheckSeverity enum values"""

    def test_severity_values(self):
        self.assertEqual(CheckSeverity.PASSED.value, "passed")
        self.assertEqual(CheckSeverity.WARNING.value, "warning")
        self.assertEqual(CheckSeverity.CRITICAL.value, "critical")
        self.assertEqual(CheckSeverity.INFO.value, "info")


class TestCheckCategory(unittest.TestCase):
    """Test CheckCategory enum values"""

    def test_category_values(self):
        self.assertEqual(CheckCategory.SYSTEM.value, "system")
        self.assertEqual(CheckCategory.NETWORK.value, "network")
        self.assertEqual(CheckCategory.STORAGE.value, "storage")
        self.assertEqual(CheckCategory.AI.value, "ai")
        self.assertEqual(CheckCategory.SECURITY.value, "security")


if __name__ == "__main__":
    unittest.main()
