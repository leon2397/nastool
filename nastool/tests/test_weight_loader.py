# -*- coding: utf-8 -*-
"""
test_weight_loader.py — Unit tests for WeightLoader

v7.0 新增测试
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.weight_loader import WeightLoader, get_weight, DEFAULT_WEIGHT


class TestWeightLoader(unittest.TestCase):
    """Test WeightLoader"""

    def setUp(self):
        self.loader = WeightLoader()

    def test_default_weights(self):
        """测试默认权重"""
        # critical 项
        self.assertEqual(self.loader.get_weight("smart_health"), 3.0)
        self.assertEqual(self.loader.get_weight("login_failures"), 3.0)
        
        # important 项
        self.assertEqual(self.loader.get_weight("gpu_detected"), 2.0)
        self.assertEqual(self.loader.get_weight("memory_check"), 2.0)
        
        # standard 项
        self.assertEqual(self.loader.get_weight("process_count"), 0.5)

    def test_unknown_check_id(self):
        """测试未知检查项返回默认权重"""
        self.assertEqual(self.loader.get_weight("unknown_check"), DEFAULT_WEIGHT)

    def test_override(self):
        """测试权重覆盖"""
        self.loader.override({
            "gpu_detected": 3.0,
            "nvidia_driver_version": 3.0,
        })
        
        self.assertEqual(self.loader.get_weight("gpu_detected"), 3.0)
        self.assertEqual(self.loader.get_weight("nvidia_driver_version"), 3.0)
        
        # 未覆盖的项保持不变
        self.assertEqual(self.loader.get_weight("memory_check"), 2.0)

    def test_override_priority(self):
        """测试覆盖优先于默认"""
        self.loader.override({"gpu_detected": 5.0})
        self.assertEqual(self.loader.get_weight("gpu_detected"), 5.0)

    def test_reset(self):
        """测试重置覆盖"""
        self.loader.override({"gpu_detected": 5.0})
        self.loader.reset()
        
        self.assertEqual(self.loader.get_weight("gpu_detected"), 2.0)

    def test_base_score(self):
        """测试基础分"""
        self.assertEqual(self.loader.get_base_score("passed"), 100)
        self.assertEqual(self.loader.get_base_score("warning"), 65)
        self.assertEqual(self.loader.get_base_score("critical"), 0)
        self.assertEqual(self.loader.get_base_score("info"), 100)

    def test_get_all_weights(self):
        """测试获取所有权重"""
        weights = self.loader.get_all_weights()
        
        self.assertIsInstance(weights, dict)
        self.assertIn("smart_health", weights)
        self.assertIn("gpu_detected", weights)

    def test_load_from_file_not_found(self):
        """测试加载不存在的文件"""
        loader = WeightLoader()
        result = loader.load_from_file("non_existent.yaml")
        
        self.assertFalse(result)

    def test_load_from_file(self):
        """测试从配置文件加载"""
        config_file = "config/health_weights.yaml"
        loader = WeightLoader(config_file)
        
        # 验证配置文件存在
        weights = loader.get_all_weights()
        self.assertIn("smart_health", weights)
        self.assertIn("gpu_detected", weights)


class TestGlobalFunction(unittest.TestCase):
    """Test 全局函数"""

    def test_get_weight(self):
        """测试全局 get_weight 函数"""
        # 应该返回默认权重（不报错）
        weight = get_weight("gpu_detected")
        self.assertIsInstance(weight, float)
        self.assertGreater(weight, 0)


if __name__ == "__main__":
    unittest.main()
