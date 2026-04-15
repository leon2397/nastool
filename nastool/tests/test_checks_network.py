"""
test_checks_network.py — Unit tests for network checks

Covers 6 network checks:
- internet_access, dns_resolve, nas_backend
- port_conflict, nic_speed, dns_coverage
"""

import unittest
from unittest.mock import patch, MagicMock


class TestInternetAccessCheck(unittest.TestCase):
    """Test InternetAccessCheck"""

    def test_run_returns_check_result(self):
        from checks.network.internet_access import InternetAccessCheck
        from checks.base import CheckResult

        check = InternetAccessCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "internet_access")
        self.assertEqual(result.category.value, "network")

    def test_check_id_constant(self):
        from checks.network.internet_access import InternetAccessCheck

        self.assertEqual(InternetAccessCheck.check_id, "internet_access")

    def test_category_is_network(self):
        from checks.network.internet_access import InternetAccessCheck
        from checks.base import CheckCategory

        self.assertEqual(InternetAccessCheck.category, CheckCategory.NETWORK)


class TestDNSResolveCheck(unittest.TestCase):
    """Test DNSResolveCheck"""

    def test_run_returns_check_result(self):
        from checks.network.dns_resolve import DNSResolveCheck
        from checks.base import CheckResult

        check = DNSResolveCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "dns_resolve")
        self.assertEqual(result.category.value, "network")


class TestNASBackendCheck(unittest.TestCase):
    """Test NASBackendCheck"""

    def test_run_returns_check_result(self):
        from checks.network.nas_backend import NASBackendCheck
        from checks.base import CheckResult

        check = NASBackendCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "nas_backend")


class TestPortConflictCheck(unittest.TestCase):
    """Test PortConflictCheck"""

    def test_run_returns_check_result(self):
        from checks.network.port_conflict import PortConflictCheck
        from checks.base import CheckResult

        check = PortConflictCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "port_conflict")


class TestNICSpeedCheck(unittest.TestCase):
    """Test NICSpeedCheck"""

    def test_run_returns_check_result(self):
        from checks.network.nic_speed import NICSpeedCheck
        from checks.base import CheckResult

        check = NICSpeedCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "nic_speed")


class TestDNSCoverageCheck(unittest.TestCase):
    """Test DNSCoverageCheck"""

    def test_run_returns_check_result(self):
        from checks.network.dns_coverage import DNSCoverageCheck
        from checks.base import CheckResult

        check = DNSCoverageCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "dns_coverage")


class TestAllNetworkChecksRegistered(unittest.TestCase):
    """Verify all network checks are registered."""

    def test_network_checks_in_registry(self):
        from checks import list_checks

        network_check_ids = [
            "internet_access",
            "dns_resolve",
            "nas_backend",
            "port_conflict",
            "nic_speed",
            "dns_coverage",
        ]
        checks = list_checks()
        available = list(checks.keys())
        for cid in network_check_ids:
            found = any(cid in check_id for check_id in available)
            self.assertTrue(
                found, f"Check {cid} not found. Available: {available}"
            )


if __name__ == "__main__":
    unittest.main()
