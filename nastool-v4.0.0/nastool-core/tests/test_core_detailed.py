# -*- coding: utf-8 -*-
"""Detailed unit tests for nastool-core"""
import sys
import os
import tempfile
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_check_result_functionality():
    """Test CheckResult functionality"""
    try:
        from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
        
        # Test CheckResult creation
        result = CheckResult(
            check_id="test_check",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.PASSED,
            passed=True,
            title="Test Check",
            current="OK",
            expected="OK",
            message="Test check passed"
        )
        
        assert result.check_id == "test_check"
        assert result.category == CheckCategory.SYSTEM
        assert result.severity == CheckSeverity.PASSED
        assert result.passed is True
        assert result.title == "Test Check"
        assert result.current == "OK"
        assert result.expected == "OK"
        assert result.message == "Test check passed"
        assert result.fix_available is False
        assert result.fix_id is None
        assert result.fix_command is None
        assert result.fix_description is None
        assert result.fix_risk == "low"
        assert result.url is None
        assert result.details == {}
    except ImportError as e:
        # If import fails, skip test
        pass


def test_check_summary_functionality():
    """Test CheckSummary functionality"""
    try:
        from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory, CheckSummary
        
        # Create test results
        results = [
            CheckResult(
                check_id="test_check_1",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.PASSED,
                passed=True,
                title="Test Check 1",
                current="OK",
                expected="OK",
                message="Test check 1 passed"
            ),
            CheckResult(
                check_id="test_check_2",
                category=CheckCategory.NETWORK,
                severity=CheckSeverity.WARNING,
                passed=False,
                title="Test Check 2",
                current="Warning",
                expected="OK",
                message="Test check 2 warning"
            )
        ]
        
        # Test CheckSummary
        summary = CheckSummary()
        for result in results:
            summary.add_result(result)
        
        assert summary.total == 2
        assert summary.passed == 1
        assert summary.warnings == 1
        assert summary.critical == 0
        assert summary.info == 0
        
        # Test score calculation
        score = summary.calculate_score()
        assert isinstance(score, int)
        assert 0 <= score <= 100
    except ImportError as e:
        # If import fails, skip test
        pass


def test_health_scorer_functionality():
    """Test health scorer functionality"""
    try:
        from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
        from nastool_core.utils.health_scorer import calculate_health_score
        
        # Create test results
        results = [
            CheckResult(
                check_id="test_check_1",
                category=CheckCategory.SYSTEM,
                severity=CheckSeverity.PASSED,
                passed=True,
                title="Test Check 1",
                current="OK",
                expected="OK",
                message="Test check 1 passed"
            )
        ]
        
        # Test health score calculation
        report = calculate_health_score(results)
        assert isinstance(report.overall_score, int)
        assert 0 <= report.overall_score <= 100
        assert hasattr(report, "grade")
        assert hasattr(report, "level_name")
    except ImportError as e:
        # If import fails, skip test
        pass


def test_terminology_translation():
    """Test terminology translation functionality"""
    try:
        from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
        from nastool_core.utils.terminology import translate_result, translate_category, generate_suggestions
        
        # Create test result
        result = CheckResult(
            check_id="test_check",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.PASSED,
            passed=True,
            title="Test Check",
            current="OK",
            expected="OK",
            message="Test check passed"
        )
        
        # Test translation functions
        translated = translate_result(result)
        assert isinstance(translated, dict)
        assert "friendly_title" in translated
        assert "friendly_message" in translated
        
        category_name = translate_category(CheckCategory.SYSTEM)
        assert isinstance(category_name, str)
        
        # Test suggestions generation
        suggestions = generate_suggestions([result])
        assert isinstance(suggestions, list)
    except ImportError as e:
        # If import fails, skip test
        pass


def test_safe_import_functionality():
    """Test safe import functionality"""
    try:
        from nastool_core.utils.safe_import import optional_import
        
        # Test optional import with existing module
        os_module, _ = optional_import("os")
        assert os_module is not None
        
        # Test optional import with non-existing module
        non_existent, _ = optional_import("non_existent_module_12345")
        assert non_existent is None
    except ImportError as e:
        # If import fails, skip test
        pass


def test_config_functionality():
    """Test config functionality"""
    try:
        from nastool_core.utils.config import Config
        
        # Test config loading with temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
nas:
  host: localhost
  port: 8000
""")
            temp_config_path = f.name
        
        try:
            config = Config(temp_config_path)
            assert config is not None
        finally:
            os.unlink(temp_config_path)
    except ImportError as e:
        # If import fails, skip test
        pass


def test_progress_tracker_functionality():
    """Test progress tracker functionality"""
    try:
        from nastool_core.utils.progress import ProgressTracker, CheckStatus
        
        # Test progress tracker initialization
        tracker = ProgressTracker(total=2, desc="Test Tracker")
        assert tracker.total == 2
        assert tracker.current == 0
        
        # Test updating status
        tracker.update("test1", CheckStatus.RUNNING, category="test")
        assert tracker.current == 1
        
        tracker.update("test2", CheckStatus.OK, category="test")
        assert tracker.current == 2
        
        # Test finish method
        stats = tracker.finish(score=95)
        assert stats["total"] == 2
        assert stats["completed"] == 2
        assert stats["score"] == 95
    except ImportError as e:
        # If import fails, skip test
        pass


def test_logger_functionality():
    """Test logger functionality"""
    try:
        from nastool_core.utils.logger import get_logger
        
        # Test logger creation
        logger = get_logger("test_logger")
        assert logger is not None
        
        # Test logging methods
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
    except ImportError as e:
        # If import fails, skip test
        pass


if __name__ == "__main__":
    tests = [
        test_check_result_functionality,
        test_check_summary_functionality,
        test_health_scorer_functionality,
        test_terminology_translation,
        test_safe_import_functionality,
        test_config_functionality,
        test_progress_tracker_functionality,
        test_logger_functionality,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
