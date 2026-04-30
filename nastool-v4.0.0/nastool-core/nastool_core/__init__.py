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
from .device_manager import DeviceManager, Device, DeviceGroup
from .async_executor import AsyncCheckExecutor, run_checks_parallel
from .check_timeouts import CHECK_TIMEOUTS, PARALLEL_CATEGORIES
from .batch_parallel import BatchParallelExecutor, batch_diagnose_parallel
from .memory_optimizer import StreamingResultProcessor, ResultCache

__version__ = "4.0.0"
__all__ = [
    # Check engine
    "Check",
    "CheckResult",
    "CheckSeverity",
    "CheckCategory",
    "CheckSummary",
    "register_check",
    "get_check",
    "list_checks",
    "run_check",
    # Config
    "CheckConfig",
    "HealthWeightsConfig",
    # Device management
    "DeviceManager",
    "Device",
    "DeviceGroup",
]
