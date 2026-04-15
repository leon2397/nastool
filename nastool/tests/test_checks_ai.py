"""
test_checks_ai.py - Unit tests for AI acceleration checks

AI checks registered: gpu_detected, nvidia_driver_version, cuda_version,
tensorrt_version, jetpack_version, rknn_version, pytorch_version,
onnxruntime_version
"""

import unittest


AI_CHECK_IDS = [
    "gpu_detected",
    "nvidia_driver_version",
    "cuda_version",
    "tensorrt_version",
    "jetpack_version",
    "rknn_version",
    "pytorch_version",
    "onnxruntime_version",
]


class TestAllAIChecksRegistered(unittest.TestCase):
    """Verify all AI checks are registered."""

    def test_ai_checks_in_registry(self):
        from checks import list_checks

        all_checks = list_checks()
        found = [cid for cid in AI_CHECK_IDS if cid in all_checks]
        missing = [cid for cid in AI_CHECK_IDS if cid not in all_checks]
        self.assertEqual(
            len(found),
            len(AI_CHECK_IDS),
            f"Missing: {missing}. Found: {sorted(found)}",
        )


class TestGPUDetectedCheck(unittest.TestCase):
    """Test GPUDetectedCheck specifically."""

    def test_category_is_ai(self):
        from checks.base import CheckCategory

        from checks import get_check

        check_cls = get_check("gpu_detected")
        instance = check_cls()
        self.assertEqual(instance.category, CheckCategory.AI)

    def test_check_id_constant(self):
        from checks import get_check

        check_cls = get_check("gpu_detected")
        self.assertEqual(check_cls.check_id, "gpu_detected")

    def test_gpu_devices_defined(self):
        from checks import get_check

        check_cls = get_check("gpu_detected")
        instance = check_cls()
        # Should have device paths defined
        pass  # device_paths attribute varies by platform
        self.assertTrue(hasattr(instance, "GPU_DEVICES"))


class TestAICheckInterfaces(unittest.TestCase):
    """Verify each AI check has the correct interface."""

    def _test_check_interface(self, check_id: str):
        from checks import get_check

        check_cls = get_check(check_id)
        self.assertIsNotNone(check_cls, f"Check {check_id} not found")
        instance = check_cls()
        self.assertEqual(instance.check_id, check_id)
        self.assertTrue(callable(instance.run))

    def test_nvidia_driver_version_interface(self):
        self._test_check_interface("nvidia_driver_version")

    def test_cuda_version_interface(self):
        self._test_check_interface("cuda_version")

    def test_tensorrt_version_interface(self):
        self._test_check_interface("tensorrt_version")

    def test_jetpack_version_interface(self):
        self._test_check_interface("jetpack_version")

    def test_rknn_version_interface(self):
        self._test_check_interface("rknn_version")

    def test_pytorch_version_interface(self):
        self._test_check_interface("pytorch_version")

    def test_onnxruntime_version_interface(self):
        self._test_check_interface("onnxruntime_version")


if __name__ == "__main__":
    unittest.main()
