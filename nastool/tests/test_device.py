"""
test_device.py — Unit tests for core/device.py
"""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.device import CpuInfo, MemInfo, BoardInfo


class TestCpuInfo(unittest.TestCase):
    """Test CpuInfo dataclass"""

    def test_cpu_info_defaults(self):
        info = CpuInfo()
        self.assertEqual(info.model, "未知")
        self.assertEqual(info.arch, "")

    def test_cpu_info_with_values(self):
        info = CpuInfo(model="ARM Cortex-A76", cores=6, arch="aarch64", freq_mhz=2400)
        self.assertEqual(info.model, "ARM Cortex-A76")
        self.assertEqual(info.cores, 6)
        self.assertEqual(info.arch, "aarch64")
        self.assertEqual(info.freq_mhz, 2400)


class TestMemInfo(unittest.TestCase):
    """Test MemInfo dataclass"""

    def test_mem_info_defaults(self):
        info = MemInfo()
        self.assertEqual(info.total_gb, 0.0)

    def test_mem_info_with_values(self):
        info = MemInfo(total_gb=8.0, available_gb=4.0, used_percent=50.0)
        self.assertEqual(info.total_gb, 8.0)
        self.assertEqual(info.available_gb, 4.0)
        self.assertEqual(info.used_percent, 50.0)


class TestBoardInfo(unittest.TestCase):
    """Test BoardInfo dataclass"""

    def test_board_info_defaults(self):
        info = BoardInfo()
        self.assertEqual(info.model, "未知")

    def test_board_info_with_values(self):
        info = BoardInfo(model="Jetson Xavier NX", manufacturer="NVIDIA", os="Ubuntu 20.04")
        self.assertEqual(info.model, "Jetson Xavier NX")
        self.assertEqual(info.manufacturer, "NVIDIA")
        self.assertEqual(info.os, "Ubuntu 20.04")
