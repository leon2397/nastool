"""
Safe Import Module for nastool

Provides safe import utilities with graceful degradation.

Usage:
    from utils.safe_import import safe_import, optional_import

    # Required dependency - will raise error if missing
    requests = safe_import('requests', 'requests')

    # Optional dependency - returns None if missing
    yaml = optional_import('yaml', 'PyYAML')
"""

import sys
from typing import Any, Optional
from logger import get_logger

logger = get_logger(__name__)


# Track available packages
_AVAILABLE_PACKAGES = {}


def safe_import(module_name: str, package_name: str = None) -> Any:
    """
    Import a required dependency.

    Args:
        module_name: Module to import (e.g., 'requests')
        package_name: Pip package name (e.g., 'requests')

    Returns:
        Imported module

    Raises:
        ImportError: If package is not installed
    """
    package_name = package_name or module_name

    if module_name in _AVAILABLE_PACKAGES:
        return _AVAILABLE_PACKAGES[module_name]

    try:
        module = __import__(module_name)
        _AVAILABLE_PACKAGES[module_name] = module
        logger.debug(f"Successfully imported {module_name}")
        return module
    except ImportError as e:
        logger.error(f"Required package '{package_name}' not installed")
        logger.error(f"Install with: pip install {package_name}")
        raise ImportError(
            f"Required package '{package_name}' is not installed. "
            f"Install with: pip install {package_name}"
        ) from e


def optional_import(module_name: str, package_name: str = None) -> Optional[Any]:
    """
    Import an optional dependency with graceful degradation.

    Args:
        module_name: Module to import (e.g., 'yaml')
        package_name: Pip package name (e.g., 'PyYAML')

    Returns:
        Imported module or None if not available
    """
    package_name = package_name or module_name

    if module_name in _AVAILABLE_PACKAGES:
        return _AVAILABLE_PACKAGES[module_name]

    try:
        module = __import__(module_name)
        _AVAILABLE_PACKAGES[module_name] = module
        logger.debug(f"Optional package '{package_name}' available")
        return module
    except ImportError:
        logger.warning(
            f"Optional package '{package_name}' not installed - some features may be limited"
        )
        _AVAILABLE_PACKAGES[module_name] = None
        return None


def is_available(module_name: str) -> bool:
    """Check if a package is available"""
    if module_name in _AVAILABLE_PACKAGES:
        return _AVAILABLE_PACKAGES[module_name] is not None

    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


# Pre-check common dependencies
def check_dependencies():
    """Check all dependencies and log status"""
    required = [
        ("requests", "requests"),
    ]

    optional = [
        ("yaml", "PyYAML"),
        ("psutil", "psutil"),
        ("tabulate", "tabulate"),
        ("colorama", "colorama"),
    ]

    missing_required = []

    for module, package in required:
        try:
            safe_import(module, package)
        except ImportError:
            missing_required.append(package)

    for module, package in optional:
        optional_import(module, package)

    if missing_required:
        logger.error(f"Missing required packages: {', '.join(missing_required)}")
        logger.error("Install with: pip install " + " ".join(missing_required))
        return False

    return True


# Convenience variables for common imports
yaml = optional_import("yaml", "PyYAML")
psutil = optional_import("psutil", "psutil")
tabulate = optional_import("tabulate", "tabulate")
colorama = optional_import("colorama", "colorama")

YAML_AVAILABLE = yaml is not None
PSUTIL_AVAILABLE = psutil is not None
TABULATE_AVAILABLE = tabulate is not None
COLORAMA_AVAILABLE = colorama is not None


if __name__ == "__main__":
    # Test safe imports
    print("=" * 50)
    print("Dependency Check")
    print("=" * 50)
    print()

    print("Required dependencies:")
    try:
        import requests

        print("  ✅ requests - available")
    except ImportError:
        print("  ❌ requests - missing")

    print()
    print("Optional dependencies:")
    for module, package in [
        ("yaml", "PyYAML"),
        ("psutil", "psutil"),
        ("tabulate", "tabulate"),
        ("colorama", "colorama"),
    ]:
        if is_available(module):
            print(f"  ✅ {package} - available")
        else:
            print(f"  ⚠️ {package} - not installed (optional)")

    print()
    print("Status:")
    if check_dependencies():
        print("  ✅ All required dependencies satisfied")
    else:
        print("  ❌ Missing required dependencies")
