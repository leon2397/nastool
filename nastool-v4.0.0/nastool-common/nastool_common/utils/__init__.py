# Utils package for nastool-common
"""
Core utilities that have no external module dependencies.
Contains: progress bars, config validation, network helpers, etc.
"""

from nastool_common.utils.progress import ProgressBar, ProgressTracker, CheckStatus, create_tracker
from .config_validator import ValidationResult, ConfigValidator
from .registry import Registry, InstanceRegistry
from .offline_storage import (
    OfflineReport,
    OfflineConfig,
    OfflineStorage,
    OfflineModeManager,
    create_offline_storage,
)
from .smart_summary import HealthStatus, SummaryItem, SmartSummary, create_summary

__all__ = [
    # Progress
    "ProgressBar",
    "ProgressTracker",
    "CheckStatus",
    "create_tracker",
    # Config validation
    "ValidationResult",
    "ConfigValidator",
    # Registry
    "Registry",
    "InstanceRegistry",
    # Offline
    "OfflineReport",
    "OfflineConfig",
    "OfflineStorage",
    "OfflineModeManager",
    "create_offline_storage",
    # Smart summary
    "HealthStatus",
    "SummaryItem",
    "SmartSummary",
    "create_summary",
]
