"""
test_ai_accel.py — Unit tests for core/ai_accel.py
"""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_accel import ChipType, AcceleratorDevice, AIReport, detect_ai_accelerator


class TestChipType(unittest.TestCase):
    """Test ChipType class attributes"""

    def test_chip_type_has_cpu(self):
        self.assertEqual(ChipType.CPU, "cpu")

    def test_chip_type_has_nvidia(self):
        # ChipType uses NVIDIA_GPU / NVIDIA_JETSON naming
        self.assertTrue(hasattr(ChipType, "NVIDIA_GPU"))
        self.assertTrue(hasattr(ChipType, "NVIDIA_JETSON"))

    def test_chip_type_has_none(self):
        self.assertEqual(ChipType.NONE, "none")


class TestAcceleratorDevice(unittest.TestCase):
    """Test AcceleratorDevice dataclass"""

    def test_device_defaults(self):
        dev = AcceleratorDevice()
        self.assertEqual(dev.chip_type, "none")
        self.assertFalse(dev.available)

    def test_device_with_values(self):
        dev = AcceleratorDevice(chip_type="nvidia", name="Jetson Xavier NX", available=True)
        self.assertEqual(dev.chip_type, "nvidia")
        self.assertEqual(dev.name, "Jetson Xavier NX")
        self.assertTrue(dev.available)


class TestAIReport(unittest.TestCase):
    """Test AIReport dataclass"""

    def test_ai_report_empty(self):
        report = AIReport(devices=[], ok=False)
        self.assertEqual(len(report.devices), 0)
        self.assertFalse(report.ok)


class TestDetectAccelerators(unittest.TestCase):
    """Test detect_ai_accelerator function"""

    @unittest.skipIf(os.name == "nt", "detect_ai_accelerator accesses Linux-only /dev paths")
    def test_detect_returns_dict(self):
        result = detect_ai_accelerator()
        self.assertIsNotNone(result)
