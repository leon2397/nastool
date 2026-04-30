"""
NAS Backend Adapter Registry

Manage and register all NAS backend adapters.

Usage:
    from nastool_adapters import register_adapter, get_adapter, list_adapters

    # Register adapter
    register_adapter("synology", SynologyAdapter)

    # Get adapter instance
    adapter = get_adapter("synology", config)

    # List all adapters
    adapters = list_adapters()
"""

from typing import Dict, Type, Optional, List
from .base import BaseAdapter, AdapterResult
import logging

logger = logging.getLogger(__name__)

# Adapter registry
_ADAPTERS: Dict[str, Type[BaseAdapter]] = {}


def register_adapter(name: str, adapter_class: Type[BaseAdapter]) -> bool:
    """Register a NAS backend adapter"""
    if name in _ADAPTERS:
        logger.warning(f"Adapter '{name}' already exists, will be overwritten")

    if not issubclass(adapter_class, BaseAdapter):
        raise TypeError(f"{adapter_class} must be a subclass of BaseAdapter")

    _ADAPTERS[name] = adapter_class
    logger.info(f"Registered adapter: {name} ({adapter_class.__name__})")
    return True


def get_adapter(name: str, config: dict = None) -> Optional[BaseAdapter]:
    """Get a NAS backend adapter instance"""
    if name not in _ADAPTERS:
        logger.error(f"Adapter '{name}' not registered")
        return None

    adapter_class = _ADAPTERS[name]

    try:
        return adapter_class(config)
    except Exception as e:
        logger.error(f"Failed to create adapter instance: {e}")
        return None


def list_adapters() -> List[Dict[str, str]]:
    """List all registered adapters"""
    result = []
    for name, adapter_class in _ADAPTERS.items():
        result.append(
            {
                "name": name,
                "class": adapter_class.__name__,
            }
        )
    return result


def has_adapter(name: str) -> bool:
    """Check if adapter is registered"""
    return name in _ADAPTERS


def unregister_adapter(name: str) -> bool:
    """Unregister an adapter"""
    if name in _ADAPTERS:
        del _ADAPTERS[name]
        logger.info(f"Unregistered adapter: {name}")
        return True
    return False


# ========== Auto-register built-in adapters ==========


def _auto_register():
    """Auto-register built-in adapters"""
    from .mock_adapter import MockAdapter

    # Register mock adapter
    register_adapter("mock", MockAdapter)

    # Try to register other adapters if available
    try:
        from .synology import SynologyAdapter
        register_adapter("synology", SynologyAdapter)
    except ImportError:
        pass

    try:
        from .qnap import QNAPAdapter
        register_adapter("qnap", QNAPAdapter)
    except ImportError:
        pass


# Auto-register on module load
_auto_register()
