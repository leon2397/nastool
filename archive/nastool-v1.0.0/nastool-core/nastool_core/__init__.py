# nastool-core - Core check engine for NASTool
"""
NASTool Core Package

Provides the core check engine with 100+ system diagnostics:
- checks/: All check implementations organized by category
- schemas/: Data structures (CheckResult, CheckSeverity, etc.)

Usage:
    from nastool_core import run_all_checks, CheckResult, CheckSeverity
    
    results = run_all_checks(device_info)
"""

from .checks import (
    Check,
    CheckResult,
    CheckSeverity,
    CheckCategory,
    CheckSummary,
    register_check,
    get_check,
    list_checks,
    run_check,
)
from .schemas.check_config import CheckConfig
from .schemas.health_weights import HealthWeightsConfig

__version__ = "1.0.0"
__all__ = [
    "Check",
    "CheckResult",
    "CheckSeverity",
    "CheckCategory",
    "CheckSummary",
    "register_check",
    "get_check",
    "list_checks",
    "run_check",
    "CheckConfig",
    "HealthWeightsConfig",
]
