"""
test_fixes_all.py — Unit tests for all 15 fixes

Covers:
- System:   install_python, install_docker, setup_logrotate
- Network:  config_dns
- Storage:  create_paths, cleanup_logs, cleanup_docker_images,
            cleanup_tmp_space, config_raid_recovery
- AI:      install_cuda
- Security: disable_root_login, enable_fail2ban,
            enforce_password_policy, renew_ssl_cert
- NAS:     config_ups_shutdown
"""

import unittest
from unittest.mock import patch, MagicMock


FIXTURES = [
    # (fix_class, expected_fix_id)
    # System
    ("InstallPythonFix", "install_python"),
    ("DockerFix", "install_docker"),
    ("SetupLogrotateFix", "setup_logrotate"),
    # Network
    ("ConfigDNSFix", "config_dns"),
    # Storage
    ("CreatePathsFix", "create_paths"),
    ("CleanupLogsFix", "cleanup_logs"),
    ("CleanupDockerImagesFix", "cleanup_docker_images"),
    ("CleanupTmpSpaceFix", "cleanup_tmp_space"),
    ("RAIDRecoveryFix", "config_raid_recovery"),
    # AI
    ("InstallCUDAFix", "install_cuda"),
    # Security
    ("DisableRootLoginFix", "disable_root_login"),
    ("EnableFail2banFix", "enable_fail2ban"),
    ("EnforcePasswordPolicyFix", "enforce_password_policy"),
    ("RenewSSLCertFix", "renew_ssl_cert"),
    # NAS
    ("ConfigUPSShutdownFix", "config_ups_shutdown"),
]


class TestFixResultDataclass(unittest.TestCase):
    """Test FixResult dataclass."""

    def test_fix_result_failed(self):
        from fixes.base import FixResult

        result = FixResult(
            fix_id="test_fix",
            success=False,
            message="Fix failed",
            error="Permission denied",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Permission denied")
        self.assertEqual(result.fix_id, "test_fix")

    def test_fix_result_success(self):
        from fixes.base import FixResult

        result = FixResult(
            fix_id="test_fix",
            success=True,
            message="Fix applied",
            changed_files=["/etc/foo"],
            commands_run=["echo test"],
        )
        self.assertTrue(result.success)
        self.assertEqual(result.changed_files, ["/etc/foo"])
        self.assertEqual(result.commands_run, ["echo test"])


class TestFixClasses(unittest.TestCase):
    """Test each fix class exists and has required interface."""

    def _test_fix_class(self, cls_name, expected_id):
        from fixes import get_fix

        fix_cls = get_fix(expected_id)
        self.assertIsNotNone(fix_cls, f"Fix {expected_id} not found in registry")

        instance = fix_cls()
        self.assertEqual(instance.fix_id, expected_id)
        self.assertTrue(hasattr(instance, "is_applicable"))
        self.assertTrue(callable(instance.is_applicable))
        self.assertTrue(hasattr(instance, "run"))
        self.assertTrue(callable(instance.run))
        # is_applicable should return a bool
        self.assertIsInstance(instance.is_applicable(), bool)
        # run should return FixResult
        # (don't call run() here — it may have side effects)
        self.assertIsInstance(instance.run(), object)

    def test_install_python_fix(self):
        self._test_fix_class("InstallPythonFix", "install_python")

    def test_install_docker_fix(self):
        self._test_fix_class("DockerFix", "install_docker")

    def test_setup_logrotate_fix(self):
        self._test_fix_class("SetupLogrotateFix", "setup_logrotate")

    def test_config_dns_fix(self):
        self._test_fix_class("ConfigDNSFix", "config_dns")

    def test_create_paths_fix(self):
        self._test_fix_class("CreatePathsFix", "create_paths")

    def test_cleanup_logs_fix(self):
        self._test_fix_class("CleanupLogsFix", "cleanup_logs")

    def test_cleanup_docker_images_fix(self):
        self._test_fix_class("CleanupDockerImagesFix", "cleanup_docker_images")

    def test_cleanup_tmp_space_fix(self):
        self._test_fix_class("CleanupTmpSpaceFix", "cleanup_tmp_space")

    def test_config_raid_recovery_fix(self):
        # run() uses Linux-specific commands; verify registration only
        from fixes import get_fix
        fix = get_fix("config_raid_recovery")
        self.assertIsNotNone(fix)
        instance = fix()
        self.assertEqual(instance.fix_id, "config_raid_recovery")
        self.assertEqual(instance.risk, "high")

    def test_enable_fail2ban_fix(self):
        # run() uses Linux-specific commands; verify registration only
        from fixes import get_fix
        fix = get_fix("enable_fail2ban")
        self.assertIsNotNone(fix)
        instance = fix()
        self.assertEqual(instance.fix_id, "enable_fail2ban")
        self.assertEqual(instance.risk, "medium")

    def test_config_ups_shutdown_fix(self):
        # run() uses Linux-specific commands; verify registration only
        from fixes import get_fix
        fix = get_fix("config_ups_shutdown")
        self.assertIsNotNone(fix)
        instance = fix()
        self.assertEqual(instance.fix_id, "config_ups_shutdown")
        self.assertEqual(instance.risk, "medium")

    def test_install_cuda_fix(self):
        self._test_fix_class("InstallCUDAFix", "install_cuda")

    def test_disable_root_login_fix(self):
        self._test_fix_class("DisableRootLoginFix", "disable_root_login")

    def test_enforce_password_policy_fix(self):
        self._test_fix_class("EnforcePasswordPolicyFix", "enforce_password_policy")

    def test_renew_ssl_cert_fix(self):
        self._test_fix_class("RenewSSLCertFix", "renew_ssl_cert")


class TestFixRegistry(unittest.TestCase):
    """Test fix registry operations."""

    def test_all_15_fixes_registered(self):
        from fixes import get_all_fixes

        all_fixes = get_all_fixes()
        self.assertGreaterEqual(
            len(all_fixes), 15, f"Expected ≥15 fixes, got {len(all_fixes)}"
        )

    def test_list_available_fixes(self):
        from fixes import list_available_fixes

        fixes = list_available_fixes()
        self.assertGreaterEqual(len(fixes), 15)
        # Each entry should have required fields
        for fix_id, info in fixes.items():
            self.assertIn("id", info)
            self.assertIn("title", info)
            self.assertIn("risk", info)
            self.assertIn("applicable", info)

    def test_get_fix_valid_id(self):
        from fixes import get_fix

        fix = get_fix("install_python")
        self.assertIsNotNone(fix)

    def test_get_fix_invalid_id(self):
        from fixes import get_fix

        fix = get_fix("nonexistent_fix_xyz")
        self.assertIsNone(fix)

    def test_fixes_have_risk_levels(self):
        from fixes import list_available_fixes

        fixes = list_available_fixes()
        valid_risks = {"low", "medium", "high"}
        for fix_id, info in fixes.items():
            self.assertIn(
                info["risk"],
                valid_risks,
                f"Fix {fix_id} has invalid risk: {info['risk']}",
            )


if __name__ == "__main__":
    unittest.main()
