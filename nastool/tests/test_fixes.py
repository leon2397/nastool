"""
test_fixes.py — Unit tests for fixes module
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixes import get_fix, get_all_fixes, run_fix
from fixes.base import FixResult


class TestFixResult(unittest.TestCase):
    """Test FixResult dataclass"""

    def test_failed_fix(self):
        result = FixResult(
            fix_id="test_fix",
            success=False,
            message="Fix failed",
            error="Permission denied",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Permission denied")

    def test_successful_fix(self):
        result = FixResult(
            fix_id="test_fix",
            success=True,
            message="Fix applied successfully",
        )
        self.assertTrue(result.success)


class TestFixRegistry(unittest.TestCase):
    """Test fix registry functions"""

    def test_get_all_fixes_returns_list(self):
        fixes = get_all_fixes()
        self.assertIsInstance(fixes, list)
        self.assertGreater(len(fixes), 0)

    def test_get_fix_returns_class(self):
        fix_cls = get_fix("install_python")
        self.assertIsNotNone(fix_cls)
        self.assertTrue(callable(fix_cls))

    def test_get_nonexistent_fix(self):
        fix_cls = get_fix("nonexistent_fix")
        self.assertIsNone(fix_cls)

    def test_all_known_fixes_present(self):
        fixes = get_all_fixes()
        fix_ids = [f.fix_id for f in fixes]
        self.assertIn("install_python", fix_ids)
        self.assertIn("config_dns", fix_ids)
        self.assertIn("create_paths", fix_ids)
        self.assertIn("install_cuda", fix_ids)
