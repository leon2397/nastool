# -*- coding: utf-8 -*-
"""Unit tests for nastool-core"""
import sys
sys.path.insert(0, r"D:\project\nastool7\nastool-core")

def test_check_severity_enum():
    from nastool_core.checks.base import CheckSeverity
    assert CheckSeverity.INFO.value == "info"
    assert CheckSeverity.WARNING.value == "warning"
    assert CheckSeverity.CRITICAL.value == "critical"
    assert CheckSeverity.PASSED.value == "passed"

def test_check_category_enum():
    from nastool_core.checks.base import CheckCategory
    assert CheckCategory.SYSTEM.value == "system"
    assert CheckCategory.NETWORK.value == "network"
    assert CheckCategory.STORAGE.value == "storage"
    assert CheckCategory.AI.value == "ai"

def test_check_result_creation():
    from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
    result = CheckResult(
        check_id="test_001",
        category=CheckCategory.SYSTEM,
        severity=CheckSeverity.PASSED,
        passed=True,
        title="Test",
        message="Test message",
        current="value",
        expected="expected",
    )
    assert result.check_id == "test_001"
    assert result.passed == True

def test_check_summary_creation():
    from nastool_core.checks.base import CheckSummary, CheckResult, CheckSeverity, CheckCategory
    r = CheckResult(
        check_id="test", category=CheckCategory.SYSTEM,
        severity=CheckSeverity.PASSED, passed=True,
        title="T", message="M", current="c", expected="e",
    )
    summary = CheckSummary(
        total=1, passed=1, warnings=0, critical=0, info=0,
        score=100, results=[r],
    )
    assert summary.total == 1
    assert summary.score == 100

def test_list_checks():
    from nastool_core.checks import list_checks
    checks = list_checks()
    assert isinstance(checks, dict)
    assert len(checks) >= 90

def test_get_check():
    from nastool_core.checks import get_check
    cls = get_check("nvidia_driver_version")
    assert cls is not None

def test_mock_data():
    from nastool_core.data import PROFILES, PROFILE_DESCRIPTIONS
    assert "healthy" in PROFILES
    assert len(PROFILES) >= 4

def test_run_mock_checks():
    from nastool_core.checks import run_mock_checks
    result = run_mock_checks("healthy")
    assert result.score >= 90
    assert result.total >= 90

def test_health_scorer():
    from nastool_core.utils.health_scorer import calculate_health_score
    from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
    r = CheckResult(
        check_id="t", category=CheckCategory.SYSTEM,
        severity=CheckSeverity.PASSED, passed=True,
        title="T", message="M", current="c", expected="e",
    )
    report = calculate_health_score([r])
    # Returns HealthReport object with .overall_score attribute
    assert hasattr(report, 'overall_score')
    assert 0 <= report.overall_score <= 100

def test_terminology():
    from nastool_core.utils.terminology import translate_result
    from nastool_core.checks.base import CheckResult, CheckSeverity, CheckCategory
    r = CheckResult(
        check_id="nvidia_driver_version", category=CheckCategory.AI,
        severity=CheckSeverity.PASSED, passed=True,
        title="NVIDIA Driver", message="Driver OK", current="535", expected="535+",
    )
    result = translate_result(r)
    assert result is not None

if __name__ == "__main__":
    tests = [
        test_check_severity_enum,
        test_check_category_enum,
        test_check_result_creation,
        test_check_summary_creation,
        test_list_checks,
        test_get_check,
        test_mock_data,
        test_run_mock_checks,
        test_health_scorer,
        test_terminology,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed")
