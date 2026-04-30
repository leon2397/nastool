"""
test_checks_detailed.py -- 从原项目迁移的详细检测测试
"""

import unittest
from unittest.mock import patch, MagicMock

from nastool_core import (
    CheckResult,
    CheckSeverity,
    CheckCategory,
    list_checks,
    get_check,
)


class TestCheckResultDetailed(unittest.TestCase):
    """详细测试 CheckResult"""

    def test_passed_result(self):
        result = CheckResult(
            check_id="test_check",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.PASSED,
            passed=True,
            title="Test Check",
            current="ok",
            expected="ok",
            message="Test passed",
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
            current="error",
            expected="ok",
            message="Test failed",
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.severity, CheckSeverity.CRITICAL)

    def test_warning_result(self):
        result = CheckResult(
            check_id="test_check",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.WARNING,
            passed=False,
            title="Test Check",
            current="warning",
            expected="ok",
            message="Test warning",
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.severity, CheckSeverity.WARNING)


class TestCheckRegistry(unittest.TestCase):
    """测试检测注册中心"""

    def test_list_checks_returns_dict(self):
        checks = list_checks()
        self.assertIsInstance(checks, dict)
        self.assertGreater(len(checks), 0)

    def test_get_check_exists(self):
        # 测试获取存在的检测项
        checks = list_checks()
        for check_id in list(checks.keys())[:3]:  # 测试前3个
            check_cls = get_check(check_id)
            self.assertIsNotNone(check_cls)

    def test_get_check_not_exists(self):
        # 测试获取不存在的检测项
        check_cls = get_check("nonexistent_check")
        self.assertIsNone(check_cls)


class TestCheckExecution(unittest.TestCase):
    """测试检测执行（使用Mock数据）"""

    def test_mock_check_data_available(self):
        """测试 Mock 数据可用"""
        from nastool_core.data.mock_results import get_mock_result, PROFILES
        
        # 验证所有 profile 都有 mock 数据
        for profile in PROFILES:
            result = get_mock_result(profile)
            self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
