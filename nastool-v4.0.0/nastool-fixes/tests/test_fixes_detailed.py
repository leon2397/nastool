"""
test_fixes_detailed.py -- 从原项目迁移的修复测试
"""

import unittest
from unittest.mock import patch, MagicMock

from nastool_fixes import (
    Fix,
    FixResult,
    list_available_fixes,
    get_all_fixes,
    get_fix,
)


class TestFixRegistry(unittest.TestCase):
    """测试修复注册中心"""

    def test_list_available_fixes(self):
        """测试列出可用修复"""
        fixes = list_available_fixes()
        self.assertIsInstance(fixes, dict)  # 实际是 dict

    def test_get_all_fixes(self):
        """测试获取所有修复"""
        fixes = get_all_fixes()
        self.assertIsInstance(fixes, list)  # 实际是 list


class TestFixTypes(unittest.TestCase):
    """测试修复类型"""

    def test_fix_class_exists(self):
        """测试 Fix 类存在"""
        self.assertIsNotNone(Fix)

    def test_fix_result_class_exists(self):
        """测试 FixResult 类存在"""
        self.assertIsNotNone(FixResult)


if __name__ == "__main__":
    unittest.main()
