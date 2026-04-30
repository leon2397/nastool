"""
checks/registry.py - Check registry for dynamic discovery
"""

from typing import Dict, List, Type, Optional
from .base import Check, CheckResult, CheckSummary, CheckCategory


# Global registry
_CHECKS: Dict[str, Type[Check]] = {}


def register_check(check_class: Type[Check]) -> Type[Check]:
    """Decorator to register a check class"""
    instance = check_class()
    _CHECKS[instance.check_id] = check_class
    return check_class


def get_check(check_id: str) -> Optional[Type[Check]]:
    """Get a check class by ID"""
    return _CHECKS.get(check_id)


def get_all_checks() -> List[Type[Check]]:
    """Get all registered check classes"""
    return list(_CHECKS.values())


def get_checks_by_category(category: CheckCategory) -> List[Type[Check]]:
    """Get checks filtered by category"""
    return [cls for cls in _CHECKS.values() if cls.category == category]


def run_all_checks(
    skip_categories: Optional[List[CheckCategory]] = None, skip_checks: Optional[List[str]] = None
) -> CheckSummary:
    """
    Run all registered checks and return summary.

    Args:
        skip_categories: Categories to skip
        skip_checks: Check IDs to skip

    Returns:
        CheckSummary with all results
    """
    skip_categories = skip_categories or []
    skip_checks = skip_checks or []

    summary = CheckSummary()

    for check_class in _CHECKS.values():
        # Skip by category
        if check_class.category in skip_categories:
            continue

        # Skip by ID
        instance = check_class()
        if instance.check_id in skip_checks:
            continue

        # Run check
        try:
            result = instance.run()
            summary.add_result(result)
        except Exception as e:
            # Check failed with exception
            from .base import CheckSeverity

            result = CheckResult(
                check_id=instance.check_id,
                category=instance.category,
                severity=CheckSeverity.CRITICAL,
                passed=False,
                title=instance.title,
                current="error",
                expected="ok",
                message=f"Check failed: {str(e)}",
            )
            summary.add_result(result)

    summary.calculate_score()
    return summary


def run_check(check_id: str, full: bool = False, offline: bool = False) -> CheckResult:
    """Run a single check by ID.

    Args:
        check_id: Check identifier
        full: Whether to run in full mode (with benchmarks)
        offline: Whether to skip network-dependent checks

    Returns:
        CheckResult from the check
    """
    check_class = get_check(check_id)
    if check_class is None:
        return None
    instance = check_class()
    return instance.run()


def list_checks() -> Dict[str, dict]:
    """Alias for list_available_checks for backward compatibility"""
    return list_available_checks()


def list_available_checks() -> Dict[str, dict]:
    """List all available checks with metadata"""
    result = {}
    for check_class in _CHECKS.values():
        instance = check_class()
        result[instance.check_id] = {
            "id": instance.check_id,
            "category": instance.category.value if hasattr(instance.category, "value") else instance.category,
            "title": instance.title,
            "description": instance.description,
        }
    return result


def run_mock_checks(profile: str = "healthy") -> CheckSummary:
    """
    Run all checks with mock data (no real system access required).

    Args:
        profile: One of 'healthy', 'degraded', 'critical', 'mixed'

    Returns:
        CheckSummary with all mock results
    """
    from data.mock_profiles import get_mock_result, PROFILES, PROFILE_DESCRIPTIONS
    from .base import CheckSummary

    summary = CheckSummary()
    if profile not in PROFILES:
        profile = "healthy"

    for check_class in _CHECKS.values():
        instance = check_class()
        result = get_mock_result(instance.check_id, profile)
        # Override category from actual check class
        result.category = instance.category
        summary.add_result(result)

    summary.calculate_score()
    return summary
