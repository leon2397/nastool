"""
test_checks_nas.py - Unit tests for NAS checks

3 NAS checks registered: nas_version, nas_users, nas_backend
Additional NAS checks: ups_status, shared_perms, log_disk, cron_conflicts
"""

import unittest


NAS_CHECK_IDS = [
    "nas_version",
    "nas_users",
    "nas_backend",
    "ups_status",
    "shared_perms",
    "log_disk",
    "cron_conflicts",
]


class TestAllNASChecksRegistered(unittest.TestCase):
    """Verify all NAS checks are registered."""

    def test_nas_checks_in_registry(self):
        from checks import list_checks

        all_checks = list_checks()
        found = [cid for cid in NAS_CHECK_IDS if cid in all_checks]
        missing = [cid for cid in NAS_CHECK_IDS if cid not in all_checks]
        self.assertEqual(
            len(found),
            len(NAS_CHECK_IDS),
            f"Missing: {missing}. Found: {sorted(found)}",
        )


class TestNASCheckInterfaces(unittest.TestCase):
    """Verify each NAS check has the correct interface."""

    def _test_check_interface(self, check_id: str):
        from checks import get_check

        check_cls = get_check(check_id)
        self.assertIsNotNone(check_cls, f"Check {check_id} not found")
        instance = check_cls()
        self.assertEqual(instance.check_id, check_id)
        self.assertTrue(callable(instance.run))

    def test_nas_version_interface(self):
        self._test_check_interface("nas_version")

    def test_nas_users_interface(self):
        self._test_check_interface("nas_users")

    def test_nas_backend_interface(self):
        self._test_check_interface("nas_backend")


class TestNASCheckResult(unittest.TestCase):
    """Test that run() returns a valid CheckResult."""

    def _run_nas_check(self, check_id: str):
        from checks import get_check

        check_cls = get_check(check_id)
        instance = check_cls()
        result = instance.run()
        self.assertTrue(hasattr(result, "check_id"))
        self.assertTrue(hasattr(result, "passed"))
        self.assertTrue(hasattr(result, "severity"))
        return result

    def test_nas_version_run(self):
        self._run_nas_check("nas_version")

    def test_nas_backend_run(self):
        self._run_nas_check("nas_backend")


if __name__ == "__main__":
    unittest.main()
