"""
nastool Constants

Centralized constants management for paths, endpoints, and default values.
"""

from typing import Dict, Any

# Version
__version__ = "4.2.0"

# Default storage paths
DEFAULT_PATHS: Dict[str, Any] = {
    # NAS root paths
    "nas_root": "/nas",
    "media_root": "/nas/media",
    # Media subdirectories
    "media": {
        "photos": "/nas/media/photos",
        "videos": "/nas/media/videos",
        "music": "/nas/media/music",
        "documents": "/nas/media/documents",
    },
    # System paths
    "temp": "/tmp/nastool",
    "logs": "/var/log/nastool",
    "cache": "/var/cache/nastool",
    "config": "/etc/nastool",
    # Diagnostic paths to check
    "check_paths": [
        "/nas",
        "/nas/media",
        "/nas/media/photos",
        "/nas/media/videos",
        "/tmp",
    ],
}

# API endpoints
DEFAULT_ENDPOINTS: Dict[str, str] = {
    # Health and status
    "health": "/health",
    "metrics": "/metrics",
    # Device management
    "devices": "/api/devices",
    "device_register": "/api/devices/register",
    "device_heartbeat": "/api/devices/heartbeat",
    # Media management
    "media": "/api/media",
    "media_scan": "/api/media/scan",
    "media_count": "/api/media/count/by-type",
    # AI features
    "ai_status": "/api/ai/status",
    # Actions
    "actions_scan": "/api/actions/scan",
    "actions_scan_sync": "/api/actions/scan/sync",
}

# Default thresholds
DEFAULT_THRESHOLDS: Dict[str, Any] = {
    # Disk space (percentage)
    "disk_warning": 80,  # Warn at 80% usage
    "disk_critical": 95,  # Critical at 95% usage
    # Memory (percentage)
    "memory_warning": 80,
    "memory_critical": 95,
    # Temperature (Celsius)
    "temp_warning": 70,
    "temp_critical": 85,
    # Write speed (MB/s)
    "write_speed_warning": 10,  # Warn below 10 MB/s
    "write_speed_critical": 5,  # Critical below 5 MB/s
    # Network timeout (seconds)
    "network_timeout": 10,
    "network_connect_timeout": 5,
}

# Default ports
DEFAULT_PORTS: Dict[str, int] = {
    "nas_backend": 8000,
    "web_dashboard": 8080,
    "websocket": 8081,
}

# Chip manufacturer names
CHIP_MANUFACTURERS: Dict[str, str] = {
    "nvidia": "NVIDIA",
    "rockchip": "Rockchip",
    "broadcom": "Broadcom",
    "amlogic": "Amlogic",
    "allwinner": "Allwinner",
    "mediatek": "MediaTek",
    "huawei": "Huawei HiSilicon",
    "intel": "Intel",
    "amd": "AMD",
    "sophgo": "Sophgo",
}

# Check categories
CHECK_CATEGORIES: Dict[str, str] = {
    "system": "System",
    "network": "Network",
    "storage": "Storage",
    "ai": "AI Acceleration",
    "security": "Security",
}

# Fix categories
FIX_CATEGORIES: Dict[str, str] = {
    "install": "Installation",
    "config": "Configuration",
    "permission": "Permissions",
    "service": "Service Management",
}

# Exit codes
EXIT_CODES: Dict[str, int] = {
    "success": 0,
    "check_failed": 1,
    "fix_failed": 2,
    "config_error": 3,
    "permission_denied": 4,
    "network_error": 5,
    "unknown_error": 99,
}

# ANSI color codes for terminal output
ANSI_COLORS: Dict[str, str] = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
}

# Status icons (ASCII-safe for cross-platform compatibility)
STATUS_ICONS: Dict[str, str] = {
    "success": "[OK]",
    "warning": "[!]",
    "error": "[X]",
    "info": "[i]",
    "running": "[..]",
    "pending": "[~]",
    "skip": "[>>]",
    "unknown": "[?]",
}


def get_path(key: str, default: str = "") -> str:
    """Get a path from DEFAULT_PATHS with dot notation.

    Args:
        key: Dot-separated path key (e.g., "media.photos")
        default: Default value if key not found

    Returns:
        Path string or default value

    Example:
        >>> get_path("media.photos")
        '/nas/media/photos'
        >>> get_path("nonexistent", "/default")
        '/default'
    """
    keys = key.split(".")
    value = DEFAULT_PATHS

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value if isinstance(value, str) else default


def get_endpoint(name: str) -> str:
    """Get an API endpoint by name.

    Args:
        name: Endpoint name (e.g., "health", "device_register")

    Returns:
        Endpoint path string

    Raises:
        KeyError: If endpoint name not found
    """
    if name not in DEFAULT_ENDPOINTS:
        raise KeyError(f"Unknown endpoint: {name}")
    return DEFAULT_ENDPOINTS[name]


def get_threshold(name: str) -> Any:
    """Get a threshold value by name.

    Args:
        name: Threshold name (e.g., "disk_warning", "temp_critical")

    Returns:
        Threshold value

    Raises:
        KeyError: If threshold name not found
    """
    if name not in DEFAULT_THRESHOLDS:
        raise KeyError(f"Unknown threshold: {name}")
    return DEFAULT_THRESHOLDS[name]
