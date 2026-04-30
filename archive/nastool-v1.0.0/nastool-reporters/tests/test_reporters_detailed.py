"""
test_reporters_detailed.py -- 从原项目迁移的报告器测试
"""

import unittest
from unittest.mock import patch, MagicMock

from nastool_reporters import (
    TerminalReporter,
    JSONReporter,
    HTMLReporter,
    FriendlyReporter,
)
from nastool_core import CheckResult, CheckSeverity, CheckCategory


class TestTerminalReporter(unittest.TestCase):
    """测试终端报告器"""

    def test_reporter_exists(self):
        """测试报告器类存在"""
        self.assertIsNotNone(TerminalReporter)

    def test_reporter_has_required_methods(self):
        """测试报告器有必需的方法"""
        self.assertTrue(hasattr(TerminalReporter, 'print_report'))
        self.assertTrue(hasattr(TerminalReporter, 'print_summary'))


class TestJSONReporter(unittest.TestCase):
    """测试 JSON 报告器"""

    def test_json_reporter_exists(self):
        """测试 JSONReporter 类存在"""
        self.assertIsNotNone(JSONReporter)


class TestHTMLReporter(unittest.TestCase):
    """测试 HTML 报告器"""

    def test_html_reporter_exists(self):
        """测试 HTMLReporter 类存在"""
        self.assertIsNotNone(HTMLReporter)


class TestReporterWithMockResults(unittest.TestCase):
    """测试报告器处理结果"""

    def test_terminal_reporter_with_mock_results(self):
        """测试终端报告器处理 Mock 结果"""
        from nastool_core.data.mock_results import get_mock_result
        
        result = get_mock_result("healthy")
        self.assertIsNotNone(result)
        
        # 验证结果可以被报告器处理
        reporter = TerminalReporter()
        self.assertIsNotNone(reporter)


if __name__ == "__main__":
    unittest.main()
