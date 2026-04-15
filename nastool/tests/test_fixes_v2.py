# -*- coding: utf-8 -*-
"""
test_fixes_v2.py — Unit tests for FixEngineV2

v7.0 新增测试
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixes.fix_engine_v2 import FixEngineV2, FixResult, FixSnapshot


class TestFixSnapshot(unittest.TestCase):
    """Test FixSnapshot dataclass"""

    def test_create_snapshot(self):
        snapshot = FixSnapshot(
            timestamp="2026-04-15T12:00:00",
            check_id="docker_info",
            fix_id="install_docker",
            before_state={"docker_installed": False},
            after_state={"docker_installed": True},
            success=True,
        )
        self.assertEqual(snapshot.check_id, "docker_info")
        self.assertEqual(snapshot.before_state["docker_installed"], False)
        self.assertEqual(snapshot.after_state["docker_installed"], True)
        self.assertTrue(snapshot.success)


class TestFixResult(unittest.TestCase):
    """Test FixResult dataclass"""

    def test_dry_run_result(self):
        result = FixResult(
            fix_id="install_docker",
            check_id="docker_info",
            action="安装 Docker",
            success=True,
            dry_run=True,
            warning="[DRY-RUN] 将执行: 安装 Docker",
        )
        self.assertTrue(result.dry_run)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.warning)

    def test_failed_fix_result(self):
        result = FixResult(
            fix_id="install_docker",
            check_id="docker_info",
            action="安装 Docker",
            success=False,
            dry_run=False,
            error="Permission denied",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Permission denied")


class TestFixEngineV2(unittest.TestCase):
    """Test FixEngineV2"""

    def setUp(self):
        self.engine = FixEngineV2(snapshot_dir="/tmp/nastool_test_snapshots")

    def test_get_recommendations(self):
        """测试获取修复建议"""
        check_results = {
            "docker_info": {"ok": False, "error": "Docker not installed"},
            "python_version": {"ok": True},
            "storage_path": {"ok": False, "error": "Path not found"},
        }
        
        recs = self.engine.get_recommendations(check_results)
        
        # 应该返回 docker_info 和 storage_path 的建议
        check_ids = [r["check_id"] for r in recs]
        self.assertIn("docker_info", check_ids)
        self.assertIn("storage_path", check_ids)
        # python_version ok=True，不应该包含
        self.assertNotIn("python_version", check_ids)

    def test_take_snapshot(self):
        """测试拍摄快照"""
        snapshot = self.engine.take_snapshot("docker_info", "install_docker")
        
        self.assertEqual(snapshot["check_id"], "docker_info")
        self.assertEqual(snapshot["fix_id"], "install_docker")
        self.assertIn("timestamp", snapshot)

    def test_execute_fix_dry_run(self):
        """测试 dry-run 模式"""
        result = self.engine.execute_fix(
            fix_id="install_docker",
            check_id="docker_info",
            dry_run=True
        )
        
        self.assertTrue(result.dry_run)
        self.assertTrue(result.success)
        self.assertIn("DRY-RUN", result.warning)

    def test_execute_fix_unknown_fix_id(self):
        """测试执行不存在的修复"""
        result = self.engine.execute_fix(
            fix_id="unknown_fix",
            check_id="test_check",
            dry_run=False
        )
        
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn("未找到", result.error)

    def test_compare_snapshots(self):
        """测试快照对比"""
        before = {"docker_installed": False, "docker_version": None}
        after = {"docker_installed": True, "docker_version": "24.0"}
        
        diff = self.engine.compare_snapshots(before, after)
        
        self.assertIn("before", diff)
        self.assertIn("after", diff)
        self.assertEqual(diff["before"]["docker_installed"], False)
        self.assertEqual(diff["after"]["docker_version"], "24.0")


if __name__ == "__main__":
    unittest.main()
