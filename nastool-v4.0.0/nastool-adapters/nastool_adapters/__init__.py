# nastool-adapters - Device adapters for NASTool
"""
NASTool Adapters Package

Provides device connection adapters:
- BaseAdapter: Abstract base class for all adapters
- SSH adapter for remote devices
- USB adapter for local devices
- MockAdapter for testing
- Vendor-specific adapters (Synology, QNAP, Jetson, etc.)

Usage:
    from nastool_adapters import BaseAdapter, MockAdapter, detect
    
    adapter = detect()  # Auto-detect device
    device_info = adapter.get_device_info()
"""

from .base import BaseAdapter, AdapterResult, ErrorCode, AdapterError
from .detector import detect, detect_with_manual
from .mock_adapter import MockAdapter
from .registry import register_adapter, get_adapter, list_adapters
from .http_detector import RemoteHTTPDetector, detect_remote_target
from .relay_detector import RelayDetector, create_relay_detector

__version__ = "4.0.0"
__all__ = [
    "BaseAdapter",
    "AdapterResult",
    "ErrorCode",
    "AdapterError",
    "detect",
    "detect_with_manual",
    "MockAdapter",
    "register_adapter",
    "get_adapter",
    "list_adapters",
    "RemoteHTTPDetector",
    "detect_remote_target",
    "RelayDetector",
    "create_relay_detector",
]
