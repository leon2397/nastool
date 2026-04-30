"""
test_adapters_detailed.py -- 从原项目迁移的适配器测试
"""

import unittest
from unittest.mock import patch, MagicMock, Mock

from nastool_adapters import (
    BaseAdapter,
    MockAdapter,
    list_adapters,
    get_adapter,
    AdapterResult,
    AdapterError,
)


class TestBaseAdapter(unittest.TestCase):
    """测试设备适配器基类"""

    def test_adapter_base_class(self):
        """测试适配器基类存在"""
        # BaseAdapter 使用 identify, run 等方法
        self.assertTrue(hasattr(BaseAdapter, 'identify'))
        self.assertTrue(hasattr(BaseAdapter, 'run'))
        self.assertTrue(hasattr(BaseAdapter, 'NAME'))


class TestMockAdapter(unittest.TestCase):
    """测试 Mock 适配器"""

    def test_mock_adapter_exists(self):
        """测试 MockAdapter 类存在"""
        self.assertIsNotNone(MockAdapter)

    def test_mock_adapter_init(self):
        """测试 MockAdapter 初始化"""
        adapter = MockAdapter(mock_data={})
        self.assertIsNotNone(adapter)


class TestAdapterRegistry(unittest.TestCase):
    """测试适配器注册中心"""

    def test_list_adapters(self):
        """测试列出适配器"""
        adapters = list_adapters()
        self.assertIsInstance(adapters, list)
        # 检查包含 mock
        names = [a.get('name') for a in adapters]
        self.assertIn('mock', names)


if __name__ == "__main__":
    unittest.main()
