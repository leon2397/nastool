"""
test_storage.py — Unit tests for core/storage.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.storage import DiskInfo


class TestDiskInfo(unittest.TestCase):
    """Test DiskInfo dataclass"""

    def test_disk_info_defaults(self):
        info = DiskInfo()
        self.assertEqual(info.device, "")

    def test_disk_info_with_values(self):
        info = DiskInfo(device="/dev/sda1", mountpoint="/", total_gb=500, free_gb=300)
        self.assertEqual(info.device, "/dev/sda1")
        self.assertEqual(info.mountpoint, "/")
        self.assertEqual(info.total_gb, 500)
        self.assertEqual(info.free_gb, 300)
