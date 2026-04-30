# nastool_core/config package
"""Configuration module for NASTool"""

from .profiles import PROFILES, DEFAULT_PROFILE, get_profile, list_profiles

__all__ = ["PROFILES", "DEFAULT_PROFILE", "get_profile", "list_profiles"]