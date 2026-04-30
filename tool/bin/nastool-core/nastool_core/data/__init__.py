# nastool_core.data - Mock data for testing
"""
Mock device profiles for testing the NASTool diagnostic engine.

Usage:
    from nastool_core.data import get_mock_result, PROFILES, PROFILE_DESCRIPTIONS
    
    result = get_mock_result("nvidia_driver_version", "healthy")
"""

from .mock_results import (
    get_mock_result,
    PROFILES,
    PROFILE_DESCRIPTIONS,
)

__all__ = [
    "get_mock_result",
    "PROFILES",
    "PROFILE_DESCRIPTIONS",
]
