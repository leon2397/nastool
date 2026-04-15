"""
test_core.py — Unit tests for core modules
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from logger import get_logger, setup_logger
from messages import msg, set_language
from core.version_check import VersionDB


class TestConfig(unittest.TestCase):
    """Tests for Config class"""

    def test_default_values(self):
        self.assertEqual(Config.NAS_HOST, "120.77.249.3")
        self.assertEqual(Config.NAS_PORT, 8000)
        self.assertEqual(Config.WEB_PORT, 8080)
        self.assertEqual(Config.MONITOR_INTERVAL, 60)

    def test_web_url(self):
        url = Config.web_url()
        self.assertIn("8080", url)

    def test_nas_url(self):
        url = Config.nas_url()
        self.assertIn("120.77.249.3", url)


class TestLogger(unittest.TestCase):
    """Tests for Logger system"""

    def test_get_logger(self):
        logger = get_logger("test_module")
        self.assertIsNotNone(logger)
        self.assertIn("test_module", logger.name)

    def test_setup_logger(self):
        logger = setup_logger("test", level="DEBUG")
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "test")


class TestMessages(unittest.TestCase):
    """Tests for Message i18n system"""

    def test_default_language(self):
        set_language("en")
        message = msg("check.passed", check_id="test")
        self.assertIn("Passed", message)

    def test_chinese_language(self):
        set_language("zh")
        message = msg("check.passed", check_id="test")
        self.assertIn("通过", message)
        set_language("en")

    def test_template_substitution(self):
        message = msg("check.failed", check_id="disk_space", message="Low space")
        self.assertIn("disk_space", message)

    def test_missing_key(self):
        message = msg("nonexistent.key")
        self.assertIn("nonexistent.key", message)


class TestDeviceDetection(unittest.TestCase):
    """Tests for device detection"""

    def test_detect_device(self):
        from profiles.loader import detect_device

        result = detect_device()
        self.assertIsNotNone(result)

    @patch("platform.machine", return_value="x86_64")
    def test_x86_not_arm(self, mock_machine):
        from profiles.loader import detect_device

        result = detect_device()
        self.assertIsNotNone(result)


class TestVersionDB(unittest.TestCase):
    """Tests for Version Database"""

    def test_version_db_exists(self):
        # version_db is fetched lazily from GitHub on first run;
        # just verify VersionDB class exists and has expected methods
        db = VersionDB()
        self.assertIsNotNone(db)
        self.assertTrue(callable(db.get_version))

    def test_version_db_load(self):
        db = VersionDB()
        self.assertIsNotNone(db)

    def test_get_version_returns(self):
        db = VersionDB()
        # Returns Optional[VersionInfo] - check it doesn't crash
        result = db.get_version("nvidia")
        # Result can be None if not found
        self.assertTrue(result is None or hasattr(result, "version"))
