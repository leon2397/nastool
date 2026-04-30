"""
Quick Diagnostics Module for nastool

Run essential checks only for fast diagnosis.

Usage:
    from utils.quick_diagnose import quick_diagnose

    results = quick_diagnose()
"""

from typing import List, Dict, Any
from dataclasses import dataclass

from nastool_common.logger import get_logger
from nastool_core.checks import CheckResult, CheckSeverity
from nastool_common.config import Config

logger = get_logger(__name__)


# Essential checks for quick diagnosis
# NOTE: Use registry check_id (pure ID, not "category.check" format)
# These IDs must match the actual registered check IDs
QUICK_CHECKS = [
    # System essentials
    "python_version",
    "memory_check",
    "system_uptime",
    # Network essentials
    "internet_access",
    "dns_resolve",
    # Storage essentials
    "disk_space",
]

# Checks to skip in quick mode
QUICK_SKIP = [
    "ai.*",  # Skip all AI checks
    "security.*",  # Skip all security checks
    "benchmark.*",  # Skip all benchmarks
    "*.write_speed",  # Skip write speed tests
    "*.speed_test",  # Skip speed tests
]


@dataclass
class QuickResult:
    """Quick diagnosis result"""

    status: str  # healthy, degraded, critical
    score: int
    checks_passed: int
    checks_total: int
    critical_issues: List[str]
    warnings: List[str]
    details: List[CheckResult]


def quick_diagnose(checks: List[str] = None, offline: bool = False) -> QuickResult:
    """
    Run quick diagnosis with essential checks only.

    Args:
        checks: Optional list of check IDs to run (default: QUICK_CHECKS)
        offline: Run in offline mode

    Returns:
        QuickResult with status and essential information
    """
    from nastool_core.checks import run_check

    check_list = checks or QUICK_CHECKS
    results: List[CheckResult] = []

    logger.info(f"Running quick diagnosis with {len(check_list)} checks")

    for check_id in check_list:
        try:
            result = run_check(check_id, full=False, offline=offline)
            if result is not None:
                results.append(result)
        except Exception as e:
            logger.error(f"Quick check {check_id} failed: {e}")
            results.append(
                CheckResult(
                    check_id=check_id,
                    category="quick",
                    severity=CheckSeverity.CRITICAL,
                    passed=False,
                    title=f"Check {check_id}",
                    current="ERROR",
                    expected="OK",
                    message=f"Check failed: {e}",
                )
            )

    # Calculate score - use r.passed (bool), not severity enum
    passed = sum(1 for r in results if r.passed)
    warnings_list = [r for r in results if not r.passed and r.severity == CheckSeverity.WARNING]
    critical = [r for r in results if not r.passed and r.severity == CheckSeverity.CRITICAL]

    total = len(results)
    if total == 0:
        score = 0
    else:
        score = int((passed / total) * 100)

    # Determine status
    if len(critical) > 0:
        status = "critical"
    elif len(warnings_list) > 0:
        status = "degraded"
    else:
        status = "healthy"

    return QuickResult(
        status=status,
        score=score,
        checks_passed=passed,
        checks_total=total,
        critical_issues=[r.message for r in critical],
        warnings=[r.message for r in warnings_list],
        details=results,
    )


def quick_health_check() -> Dict[str, Any]:
    """
    Run ultra-fast health check (5 seconds max).

    Returns a simple dict for CI/CD pipelines:
    {
        "healthy": true/false,
        "score": 0-100,
        "issues": ["issue1", "issue2"]
    }
    """
    import time

    start = time.time()

    result = quick_diagnose()

    elapsed = time.time() - start

    return {
        "healthy": result.status == "healthy",
        "score": result.score,
        "status": result.status,
        "issues": result.critical_issues + result.warnings,
        "checks": result.checks_total,
        "passed": result.checks_passed,
        "elapsed_seconds": round(elapsed, 2),
    }


def print_quick_report(result: QuickResult) -> None:
    """Print quick diagnosis report to console"""
    print("\n" + "=" * 50)
    print("Quick Diagnosis Report")
    print("=" * 50)

    status_icons = {"healthy": "OK", "degraded": "WARN", "critical": "CRIT"}
    icon = status_icons.get(result.status, "?")

    print(f"\n{icon} Status: {result.status.upper()}")
    print(f"Score: {result.score}/100")
    print(f"Passed: {result.checks_passed}/{result.checks_total}")

    if result.critical_issues:
        print("\nCritical Issues:")
        for issue in result.critical_issues:
            print(f"   - {issue}")

    if result.warnings:
        print("\nWarnings:")
        for issue in result.warnings:
            print(f"   - {issue}")

    print("\n" + "-" * 50)
    if result.status == "healthy":
        print("System is healthy. No action required.")
    elif result.status == "degraded":
        print("System has warnings. Consider running full diagnosis:")
        print("   python3 arm_diagnose.py --full")
    else:
        print("System has critical issues. Run diagnostics with fix:")
        print("   python3 arm_diagnose.py --fix")

    print("=" * 50)


if __name__ == "__main__":
    result = quick_diagnose()
    print_quick_report(result)
