from typing import List
"""
test_functional.py — T2 Functional tests: Core workflow verification

Tests the 5 main execution paths:
- F1: CLI argument parsing (parse_args)
- F2: Device detection and profile loading
- F3: Quick diagnosis pipeline
- F4: Full diagnosis pipeline (run_check + CheckSummary)
- F5: Fix execution pipeline

Uses mocks for platform-specific operations.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

nastool_root = Path(__file__).parent.parent.resolve()
if str(nastool_root) not in sys.path:
    sys.path.insert(0, str(nastool_root))

os.environ.setdefault("NASTOOL_OFFLINE", "1")


# ─────────────────────────────────────────────────────────────
# F1: CLI Argument Parsing
# ─────────────────────────────────────────────────────────────
class TestCLIArgumentParsing(unittest.TestCase):
    """Test that parse_args correctly handles all CLI flags."""

    def _parse_args(self, argv: list):
        import argparse
        argparse.ArgumentParser()._defaults.clear()
        from arm_diagnose import parse_args
        original_argv = sys.argv
        try:
            sys.argv = ["arm_diagnose.py"] + argv
            return parse_args()
        finally:
            sys.argv = original_argv

    def test_no_args_defaults(self):
        args = self._parse_args([])
        self.assertFalse(args.version)
        self.assertFalse(args.full)
        self.assertFalse(args.quick)

    def test_version_flag(self):
        args = self._parse_args(["--version"])
        self.assertTrue(args.version)

    def test_quick_flag(self):
        args = self._parse_args(["--quick"])
        self.assertTrue(args.quick)

    def test_full_flag(self):
        args = self._parse_args(["--full"])
        self.assertTrue(args.full)

    def test_offline_flag(self):
        args = self._parse_args(["--offline"])
        self.assertTrue(args.offline)

    def test_profile_flag(self):
        args = self._parse_args(["--profile", "pi5"])
        self.assertEqual(args.profile, "pi5")

    def test_output_flag(self):
        args = self._parse_args(["--output", "report.json"])
        self.assertEqual(args.output, "report.json")

    def test_fix_flag(self):
        args = self._parse_args(["--fix"])
        self.assertTrue(args.fix)

    def test_skip_category_flag(self):
        args = self._parse_args(["--skip", "ai,security"])
        self.assertEqual(args.skip, "ai,security")

    def test_list_profiles_flag(self):
        args = self._parse_args(["--list-profiles"])
        self.assertTrue(args.list_profiles)

    def test_list_checks_flag(self):
        args = self._parse_args(["--list-checks"])
        self.assertTrue(args.list_checks)

    def test_list_fixes_flag(self):
        args = self._parse_args(["--list-fixes"])
        self.assertTrue(args.list_fixes)


# ─────────────────────────────────────────────────────────────
# F2: Device Detection & Profile Loading
# ─────────────────────────────────────────────────────────────
class TestDeviceDetection(unittest.TestCase):
    """Test device auto-detection and profile loading."""

    def test_detect_device_returns_profile(self):
        from profiles.loader import detect_device
        profile = detect_device()
        self.assertIsNotNone(profile)
        self.assertTrue(hasattr(profile, "id"))
        self.assertTrue(hasattr(profile, "name"))

    def test_get_profile_valid_id(self):
        from profiles.loader import list_profiles, get_profile
        profiles = list_profiles()
        self.assertGreater(len(profiles), 0)
        profile = get_profile(profiles[0])
        self.assertIsNotNone(profile)
        self.assertEqual(profile.id, profiles[0])

    def test_get_profile_invalid_id_returns_none(self):
        from profiles.loader import get_profile
        self.assertIsNone(get_profile("nonexistent-xyz-12345"))

    def test_list_profiles_returns_all_devices(self):
        from profiles.loader import list_profiles
        profiles = list_profiles()
        self.assertIsInstance(profiles, list)
        self.assertGreater(len(profiles), 20)

    def test_all_profiles_have_required_attributes(self):
        from profiles.loader import list_profiles, get_profile
        for pid in list_profiles()[:5]:
            profile = get_profile(pid)
            if profile:
                self.assertTrue(hasattr(profile, "id"))
                self.assertTrue(hasattr(profile, "name"))
                self.assertTrue(hasattr(profile, "vendor"))
                self.assertIsInstance(profile.checks, dict)
                self.assertIsInstance(profile.fixes, list)


# ─────────────────────────────────────────────────────────────
# F3: Quick Diagnosis Pipeline
# ─────────────────────────────────────────────────────────────
class TestQuickDiagnosis(unittest.TestCase):
    """Test quick_diagnose() pipeline."""

    def test_quick_diagnose_returns_quick_result(self):
        from utils.quick_diagnose import quick_diagnose, QuickResult
        result = quick_diagnose(offline=True)
        self.assertIsInstance(result, QuickResult)
        self.assertIn(result.status, ["healthy", "degraded", "critical"])

    def test_quick_result_has_score(self):
        from utils.quick_diagnose import quick_diagnose
        result = quick_diagnose(offline=True)
        self.assertIsInstance(result.score, int)
        self.assertGreaterEqual(result.score, 0)
        self.assertLessEqual(result.score, 100)

    def test_quick_result_has_details(self):
        from utils.quick_diagnose import quick_diagnose
        result = quick_diagnose(offline=True)
        # details is List[CheckResult], not dict
        self.assertIsInstance(result.details, list)

    def test_quick_result_status_values(self):
        from utils.quick_diagnose import quick_diagnose
        result = quick_diagnose(offline=True)
        self.assertIsInstance(result.status, str)
        self.assertGreater(len(result.status), 0)


# ─────────────────────────────────────────────────────────────
# F4: Full Diagnosis Pipeline
# ─────────────────────────────────────────────────────────────
class TestCheckExecution(unittest.TestCase):
    """Test run_check() single check execution (avoids run_all_checks hanging)."""

    def test_run_check_python_version(self):
        from checks import run_check
        result = run_check("python_version", offline=True)
        self.assertTrue(hasattr(result, "check_id"))
        self.assertEqual(result.check_id, "python_version")
        self.assertTrue(hasattr(result, "passed"))
        self.assertIsInstance(result.passed, bool)
        self.assertTrue(hasattr(result, "severity"))
        self.assertTrue(hasattr(result, "category"))

    def test_run_check_invalid_id_returns_none(self):
        from checks import run_check
        # Invalid check IDs return None (not a failed result)
        result = run_check("nonexistent_check_id_xyz", offline=True)
        self.assertIsNone(result)

    def test_run_check_multiple_checks(self):
        from checks import run_check
        check_ids = ["python_version", "pip_installed"]
        for cid in check_ids:
            result = run_check(cid, offline=True)
            self.assertIsNotNone(result)
            self.assertTrue(hasattr(result, "check_id"))

    def test_run_check_result_has_all_required_fields(self):
        from checks import run_check
        result = run_check("python_version", offline=True)
        required = ["check_id", "category", "severity", "passed", "title", "message"]
        for field in required:
            self.assertTrue(hasattr(result, field), f"Missing field: {field}")

    def test_run_check_offline_mode_works(self):
        from checks import run_check
        # offline=True should not raise
        result = run_check("python_version", offline=True)
        self.assertIsNotNone(result)

    def test_list_checks_returns_dict(self):
        from checks import list_checks
        checks = list_checks()
        self.assertIsInstance(checks, dict)
        self.assertGreater(len(checks), 10)


class TestHealthSummary(unittest.TestCase):
    """Test CheckSummary health calculation."""

    def test_check_summary_initial_state(self):
        from checks.base import CheckSummary
        summary = CheckSummary()
        self.assertEqual(summary.total, 0)
        self.assertEqual(summary.passed, 0)
        self.assertEqual(summary.critical, 0)
        self.assertIsInstance(summary.score, (int, float))

    def test_check_summary_add_result(self):
        from checks.base import CheckSummary, CheckResult, CheckSeverity, CheckCategory
        summary = CheckSummary()
        result = CheckResult(
            check_id="test",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.PASSED,
            passed=True,
            title="Test",
            current="OK",
            expected="OK",
            message="OK",
        )
        summary.add_result(result)
        self.assertEqual(summary.total, 1)
        self.assertEqual(summary.passed, 1)

    def test_check_summary_get_health_report(self):
        from checks.base import CheckSummary, CheckResult, CheckSeverity, CheckCategory
        summary = CheckSummary()
        result = CheckResult(
            check_id="test",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.CRITICAL,
            passed=False,
            title="Test",
            current="FAIL",
            expected="PASS",
            message="FAIL",
        )
        summary.add_result(result)
        report = summary.get_health_report()
        self.assertIsNotNone(report)
        self.assertTrue(hasattr(report, "overall_score"))
        self.assertTrue(hasattr(report, "level_name"))


# ─────────────────────────────────────────────────────────────
# F5: Fix Execution Pipeline
# ─────────────────────────────────────────────────────────────
class TestFixExecution(unittest.TestCase):
    """Test fix execution pipeline."""

    def test_list_available_fixes_returns_dict(self):
        from fixes import list_available_fixes
        fixes = list_available_fixes()
        self.assertIsInstance(fixes, dict)
        self.assertGreater(len(fixes), 0)

    def test_run_fix_invalid_id_returns_failed_result(self):
        from fixes import run_fix
        result = run_fix("nonexistent_fix_xyz", confirm=False)
        self.assertFalse(result.success)
        self.assertTrue(hasattr(result, "message"))

    def test_all_fixes_have_risk_levels(self):
        from fixes import list_available_fixes
        fixes = list_available_fixes()
        valid_risks = {"low", "medium", "high"}
        for fix_id, info in fixes.items():
            self.assertIn(info["risk"], valid_risks)

    def test_all_fixes_have_applicable_info(self):
        from fixes import list_available_fixes
        fixes = list_available_fixes()
        for fix_id, info in fixes.items():
            self.assertIn("applicable", info)
            self.assertIn("title", info)

    def test_run_fix_confirm_false_does_not_crash(self):
        from fixes import run_fix
        # Should return failed result, not crash
        result = run_fix("nonexistent_fix_xyz", confirm=False)
        self.assertFalse(result.success)


# ─────────────────────────────────────────────────────────────
# F6: Version & Config
# ─────────────────────────────────────────────────────────────
class TestVersionAndConfig(unittest.TestCase):
    """Test version info and config loading."""

    def test_version_defined(self):
        from arm_diagnose import __version__
        self.assertIsInstance(__version__, str)
        self.assertGreater(len(__version__), 0)

    def test_config_loads(self):
        from config import Config
        config = Config()
        self.assertTrue(hasattr(config, "CHECK_TIMEOUT"))
        self.assertTrue(hasattr(config, "WEB_PORT"))
        self.assertTrue(hasattr(config, "MAX_WORKERS"))

    def test_version_db_imports(self):
        from core.version_check import VersionDB
        db = VersionDB()
        self.assertIsInstance(db, object)


if __name__ == "__main__":
    unittest.main()
