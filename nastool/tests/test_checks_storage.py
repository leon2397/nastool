"""
test_checks_storage.py - Unit tests for storage checks

9 storage checks registered: disk_space, smart_health, hdd_temperature,
raid_status, storage_trend, docker_images, write_speed, path_exists, log_disk
"""

import unittest


STORAGE_CHECK_IDS = [
    "disk_space",
    "smart_health",
    "hdd_temperature",
    "raid_status",
    "storage_trend",
    "docker_images",
    "write_speed",
    "path_exists",
    "log_disk",
]


class TestAllStorageChecksRegistered(unittest.TestCase):
    """Verify all 9 storage checks are registered."""

    def test_storage_checks_in_registry(self):
        from checks import list_checks

        all_checks = list_checks()
        found = [cid for cid in STORAGE_CHECK_IDS if cid in all_checks]
        missing = [cid for cid in STORAGE_CHECK_IDS if cid not in all_checks]
        self.assertEqual(
            len(found),
            len(STORAGE_CHECK_IDS),
            f"Missing: {missing}. Found: {sorted(found)}",
        )


class TestStorageCheckInterfaces(unittest.TestCase):
    """Verify each storage check has the correct interface."""

    def _test_check_interface(self, check_id: str):
        from checks import get_check

        check_cls = get_check(check_id)
        self.assertIsNotNone(check_cls, f"Check {check_id} not found")

        instance = check_cls()
        self.assertTrue(hasattr(instance, "check_id"))
        self.assertEqual(instance.check_id, check_id)
        self.assertTrue(hasattr(instance, "run"))
        self.assertTrue(callable(instance.run))

    def test_disk_space_interface(self):
        self._test_check_interface("disk_space")

    def test_smart_health_interface(self):
        self._test_check_interface("smart_health")

    def test_hdd_temperature_interface(self):
        self._test_check_interface("hdd_temperature")

    def test_raid_status_interface(self):
        self._test_check_interface("raid_status")

    def test_storage_trend_interface(self):
        self._test_check_interface("storage_trend")

    def test_docker_images_interface(self):
        self._test_check_interface("docker_images")

    def test_write_speed_interface(self):
        self._test_check_interface("write_speed")

    def test_path_exists_interface(self):
        self._test_check_interface("path_exists")

    def test_log_disk_interface(self):
        self._test_check_interface("log_disk")


class TestStorageCheckResult(unittest.TestCase):
    """Test that run() returns a valid CheckResult (mocked on Windows)."""

    def _run_stored_check(self, check_id: str):
        from checks import get_check

        check_cls = get_check(check_id)
        instance = check_cls()
        # On Windows, many storage checks will fail (no /proc/mdstat, etc.)
        # Just verify run() returns something with the right attributes
        result = instance.run()
        self.assertTrue(hasattr(result, "check_id"))
        self.assertTrue(hasattr(result, "passed"))
        self.assertTrue(hasattr(result, "severity"))
        return result

    def test_disk_space_run(self):
        self._run_stored_check("disk_space")

    def test_smart_health_run(self):
        self._run_stored_check("smart_health")

    def test_path_exists_run(self):
        self._run_stored_check("path_exists")


if __name__ == "__main__":
    unittest.main()
