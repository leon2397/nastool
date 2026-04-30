# nastool-common - Common utilities for NASTool
"""
NASTool Common Package

Provides shared utilities used across all NASTool modules:
- config: Configuration management
- logger: Logging utilities
- exceptions: Custom exception classes
- messages: Message templates
- utils: Utility functions
"""

from .config import Config
from .logger import get_logger, setup_logger
from .exceptions import (
    NastoolError,
    CheckFailedError,
    FixFailedError,
    DeviceNotDetectedError,
    ProfileNotFoundError,
    ConfigurationError,
    NetworkError,
    DependencyError,
    StorageError,
)
from .messages import msg, set_language, get_message

__version__ = "1.0.0"
__all__ = [
    "Config",
    "get_logger",
    "setup_logger",
    "NastoolError",
    "CheckFailedError",
    "FixFailedError",
    "DeviceNotDetectedError",
    "ProfileNotFoundError",
    "ConfigurationError",
    "NetworkError",
    "DependencyError",
    "StorageError",
    "msg",
    "set_language",
    "get_message",
]
