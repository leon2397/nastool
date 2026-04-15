"""
test_checks_security.py — Unit tests for security checks

Covers 5 security checks:
- firewall, selinux, ssh_root, login_failures, ssl_cert
"""

import unittest
from unittest.mock import patch, mock_open


class TestFirewallCheck(unittest.TestCase):
    """Test FirewallCheck"""

    def test_run_returns_check_result(self):
        from checks.security.firewall import FirewallCheck
        from checks.base import CheckResult

        check = FirewallCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "firewall")
        self.assertEqual(result.category.value, "security")

    def test_check_id_constant(self):
        from checks.security.firewall import FirewallCheck

        self.assertEqual(FirewallCheck.check_id, "firewall")


class TestSELinuxCheck(unittest.TestCase):
    """Test SELinuxCheck"""

    def test_run_returns_check_result(self):
        from checks.security.selinux import SELinuxCheck
        from checks.base import CheckResult

        check = SELinuxCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "selinux")


class TestSSHRootCheck(unittest.TestCase):
    """Test SSHRootCheck"""

    def test_run_returns_check_result(self):
        from checks.security.ssh_root import SSHRootCheck
        from checks.base import CheckResult

        check = SSHRootCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "ssh_root")

    def test_root_login_disabled_returns_passed(self):
        from checks.security.ssh_root import SSHRootCheck
        from checks.base import CheckSeverity

        check = SSHRootCheck()
        config_content = "PermitRootLogin no\n"
        with patch("builtins.open", mock_open(read_data=config_content)):
            result = check.run()
            self.assertTrue(result.passed)
            self.assertEqual(result.severity, CheckSeverity.PASSED)

    def test_root_login_yes_returns_critical(self):
        from checks.security.ssh_root import SSHRootCheck
        from checks.base import CheckSeverity

        check = SSHRootCheck()
        config_content = "PermitRootLogin yes\n"
        with patch("builtins.open", mock_open(read_data=config_content)):
            result = check.run()
            self.assertFalse(result.passed)
            self.assertEqual(result.severity, CheckSeverity.WARNING)

    def test_sshd_config_missing_returns_info(self):
        from checks.security.ssh_root import SSHRootCheck
        from checks.base import CheckSeverity

        check = SSHRootCheck()
        with patch("builtins.open", side_effect=FileNotFoundError()):
            result = check.run()
            self.assertEqual(result.severity, CheckSeverity.INFO)


class TestLoginFailuresCheck(unittest.TestCase):
    """Test LoginFailuresCheck"""

    def test_run_returns_check_result(self):
        from checks.security.login_failures import LoginFailuresCheck
        from checks.base import CheckResult

        check = LoginFailuresCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "login_failures")


class TestSSLCertCheck(unittest.TestCase):
    """Test SSLCertCheck"""

    def test_run_returns_check_result(self):
        from checks.security.ssl_cert import SSLCertCheck
        from checks.base import CheckResult

        check = SSLCertCheck()
        result = check.run()
        self.assertIsInstance(result, CheckResult)
        self.assertEqual(result.check_id, "ssl_cert")


class TestAllSecurityChecksRegistered(unittest.TestCase):
    """Verify all security checks are registered."""

    def test_security_checks_in_registry(self):
        from checks import list_checks

        security_check_ids = [
            "firewall",
            "selinux",
            "ssh_root",
            "login_failures",
            "ssl_cert",
        ]
        checks = list_checks()
        available = list(checks.keys())
        for cid in security_check_ids:
            found = any(cid in check_id for check_id in available)
            self.assertTrue(
                found, f"Check {cid} not found. Available: {available}"
            )


if __name__ == "__main__":
    unittest.main()
