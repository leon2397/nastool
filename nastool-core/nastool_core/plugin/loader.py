"""
plugin/loader.py - Plugin discovery and loading

Supports three discovery mechanisms:
1. Python entry_points (pip-installed packages)
2. Directory scan (local .py files)
3. Explicit class registration (programmatic)

Note: All imports from nastool_core.checks and nastool_adapters are lazy
(to avoid circular import issues with the adapter layer).
"""

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type

from .base import NastoolPlugin
from .registry import plugin_registry

logger = logging.getLogger(__name__)

# entry_point group name for nastool plugins
ENTRY_POINT_GROUP = "nastool.plugins"


def discover_entrypoints() -> Dict[str, Type[NastoolPlugin]]:
    """
    Discover plugins installed via pip entry_points.

    To register a plugin via entry_points, add to setup.cfg/pyproject.toml:

        [project.entry-points."nastool.plugins"]
        my-plugin = "my_package.plugin:MyPlugin"

    Returns:
        Dict mapping plugin name -> plugin class
    """
    discovered = {}

    try:
        from importlib.metadata import entry_points

        eps = entry_points()
        plugin_eps = eps.get(ENTRY_POINT_GROUP, [])

        for ep in plugin_eps:
            try:
                plugin_class = ep.load()
                if not issubclass(plugin_class, NastoolPlugin):
                    logger.warning(
                        f"Entry point '{ep.name}' is not a NastoolPlugin subclass, skipping"
                    )
                    continue

                discovered[plugin_class.name] = plugin_class
                logger.info(f"Discovered plugin via entry_point: {plugin_class.name}")
            except Exception as e:
                logger.error(f"Failed to load plugin from entry point '{ep.name}': {e}")

    except ImportError:
        # Python < 3.10 fallback
        try:
            from importlib_metadata import entry_points
            eps = entry_points()
            plugin_eps = eps.get(ENTRY_POINT_GROUP, [])

            for ep in plugin_eps:
                try:
                    plugin_class = ep.load()
                    if not issubclass(plugin_class, NastoolPlugin):
                        continue
                    discovered[plugin_class.name] = plugin_class
                    logger.info(f"Discovered plugin: {plugin_class.name}")
                except Exception as e:
                    logger.error(f"Failed to load '{ep.name}': {e}")
        except ImportError:
            logger.warning("Neither importlib.metadata nor importlib_metadata available")

    return discovered


def discover_directory(
    plugin_dir: str,
    auto_register: bool = True,
) -> Dict[str, Type[NastoolPlugin]]:
    """
    Discover plugins from a local directory.

    Directory layout:
        plugin_dir/
        ├── __init__.py        (optional)
        ├── my_plugin.py        <- contains MyPlugin(NastoolPlugin)
        └── another/
            └── plugin.py      <- contains AnotherPlugin(NastoolPlugin)

    Args:
        plugin_dir: Path to plugin directory
        auto_register: Register discovered classes immediately

    Returns:
        Dict mapping plugin name -> plugin class
    """
    discovered = {}
    plugin_path = Path(plugin_dir).expanduser().resolve()

    if not plugin_path.exists():
        logger.debug(f"Plugin directory does not exist: {plugin_path}")
        return discovered

    if not plugin_path.is_dir():
        logger.warning(f"Plugin path is not a directory: {plugin_path}")
        return discovered

    # Add to sys.path so plugins can import each other
    parent = str(plugin_path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    for item in plugin_path.rglob("*.py"):
        # Skip __init__ and private files
        if item.name.startswith("_"):
            continue

        module_name = item.stem

        # Compute dotted module path
        try:
            relative = item.relative_to(plugin_path.parent)
            dotted = str(relative.with_suffix("")).replace(os.sep, ".")
        except ValueError:
            dotted = module_name

        try:
            # Try importing as dotted module first
            spec = importlib.util.spec_from_file_location(dotted, item)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[dotted] = module
                spec.loader.exec_module(module)

                # Find all NastoolPlugin subclasses
                for attr_name in dir(module):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, NastoolPlugin)
                        and attr is not NastoolPlugin
                    ):
                        discovered[attr.name] = attr
                        if auto_register:
                            plugin_registry.register_class(attr)
                        logger.info(f"Discovered plugin: {attr.name} ({dotted}.{attr_name})")

        except Exception as e:
            logger.error(f"Failed to load plugin from {item}: {e}")

    return discovered


def load_plugin(
    plugin_class: Type[NastoolPlugin],
    config: Optional[Dict] = None,
) -> Optional[NastoolPlugin]:
    """
    Instantiate and load a plugin.

    Loads:
    1. Calls on_load(config)
    2. Registers checks via register_checks()
    3. Registers adapters via register_adapters()

    Args:
        plugin_class: Plugin class to instantiate
        config: Optional plugin configuration dict

    Returns:
        Plugin instance if successful, None otherwise
    """
    name = plugin_class.name

    if name in plugin_registry.instances:
        logger.warning(f"Plugin '{name}' already loaded, skipping")
        return plugin_registry.instances[name]

    try:
        instance = plugin_class()

        # Lifecycle: on_load
        instance.on_load(config)

        # Register checks (lazy import to avoid circular deps)
        for check_class in instance.register_checks():
            from nastool_core.checks.registry import register_check

            register_check(check_class)
            logger.debug(f"  -> registered check: {check_class.check_id}")

        # Register adapters (lazy import to avoid circular deps)
        for adapter_name, adapter_class in instance.register_adapters():
            from nastool_adapters.registry import register_adapter

            register_adapter(adapter_name, adapter_class)
            logger.debug(f"  -> registered adapter: {adapter_name}")

        # Store instance
        plugin_registry._plugins[name] = instance

        logger.info(f"Loaded plugin: {name} v{plugin_class.version}")
        return instance

    except Exception as e:
        logger.error(f"Failed to load plugin '{name}': {e}")
        plugin_registry._failed[name] = str(e)
        return None


def unload_plugin(name: str) -> bool:
    """
    Unload a plugin.

    1. Calls on_unload()
    2. Removes from registry

    Note: Registered checks/adapters are NOT unregistered.
    This is by design — removing checks mid-run could break things.
    """
    instance = plugin_registry.get_instance(name)
    if not instance:
        logger.warning(f"Plugin '{name}' not loaded")
        return False

    try:
        instance.on_unload()
        del plugin_registry._plugins[name]
        logger.info(f"Unloaded plugin: {name}")
        return True
    except Exception as e:
        logger.error(f"Error unloading plugin '{name}': {e}")
        return False
