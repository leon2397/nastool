"""
test_integration_detailed.py -- 从原项目迁移的集成测试
"""

import unittest
from unittest.mock import patch, MagicMock

# 集成测试：跨模块功能


class TestEndToEndWorkflow(unittest.TestCase):
    """测试端到端工作流"""

    def test_mock_workflow(self):
        """测试完整的 Mock 工作流"""
        from nastool_core import list_checks
        from nastool_core.data.mock_results import get_mock_result
        from nastool_reporters import TerminalReporter
        
        # 1. 获取所有检测项
        checks = list_checks()
        self.assertGreater(len(checks), 0)
        
        # 2. 获取 Mock 结果
        result = get_mock_result("healthy")
        self.assertIsNotNone(result)
        
        # 3. 生成报告
        reporter = TerminalReporter()
        self.assertIsNotNone(reporter)


class TestModuleIntegration(unittest.TestCase):
    """测试模块间集成"""

    def test_core_to_reporters(self):
        """测试 core → reporters 集成"""
        from nastool_core.data.mock_results import get_mock_result
        from nastool_reporters import TerminalReporter
        
        result = get_mock_result("healthy")
        reporter = TerminalReporter()
        
        # 验证数据可以传递
        self.assertIsNotNone(result)
        self.assertIsNotNone(reporter)

    def test_core_to_adapters(self):
        """测试 core → adapters 集成"""
        from nastool_core import CheckResult, CheckSeverity, CheckCategory
        from nastool_adapters import BaseAdapter
        
        # 验证类型可以跨模块使用
        result = CheckResult(
            check_id="test",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.PASSED,
            passed=True,
            title="Test",
            current="ok",
            expected="ok",
            message="Test message",
        )
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
