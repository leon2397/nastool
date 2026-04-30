"""
plugin/manager.py - High-level plugin manager

Provides a single entry point for:
- Discovering all plugins (entry_points + directories)
- Loading all plugins
- Querying plugin status
- Managing the plugin lifecycle
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Type

from .base import NastoolPlugin, PluginMetadata
from .loader import (
    discover_entrypoints,
    discover_directory,
    load_plugin,
    unload_plugin,
)
from .registry import plugin_registry

logger = logging.getLogger(__name__)


class PluginManager:
    """
    High-level plugin manager.

    Discovers and loads plugins from:
    1. pip-installed packages (entry_points)
    2. ~/.nastool/plugins/ directory (local files)

    Usage:
        manager = PluginManager()
        manager.discover_all()
        manager.load_all()
        print(manager.list())
    """

    def __init__(
        self,
        plugin_dirs: Optional[List[str]] = None,
        auto_load: bool = True,
    ):
        """
        Initialize plugin manager.

        Args:
            plugin_dirs: Extra directories to scan for plugins
            auto_load: If True, discover and load on init
        """
        self._plugin_dirs = plugin_dirs or []

        if auto_load:
            self.discover_all()
            self.load_all()

    # ── Discovery ───────────────────────────────────────

    def discover_all(self) -> Dict[str, Type[NastoolPlugin]]:
        """
        Discover all available plugins from all sources.

        Returns:
            Dict of discovered plugin classes
        """
        discovered = {}

        # 1. entry_points (pip-installed)
        eps = discover_entrypoints()
        discovered.update(eps)
        logger.info(f"Discovered {len(eps)} plugin(s) from entry_points")

        # 2. user plugin directory
        user_dir = self._get_user_plugin_dir()
        if user_dir:
            local = discover_directory(str(user_dir), auto_register=False)
            # Don't overwrite entry_point plugins with local ones
            for name, cls in local.items():
                if name not in discovered:
                    discovered[name] = cls
            logger.info(f"Discovered {len(local)} plugin(s) from {user_dir}")

        # 3. extra directories
        for extra_dir in self._plugin_dirs:
            extra = discover_directory(extra_dir, auto_register=False)
            for name, cls in extra.items():
                if name not in discovered:
                    discovered[name] = cls
            logger.info(f"Discovered {len(extra)} plugin(s) from {extra_dir}")

        return discovered

    def _get_user_plugin_dir(self) -> Optional[Path]:
        """Get the user's local plugin directory."""
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base = Path.home() / ".config"
        user_dir = base / "nastool" / "plugins"
        return user_dir if user_dir.exists() else None

    # ── Loading ───────────────────────────────────────

    def load_all(
        self,
        config: Optional[Dict] = None,
        whitelist: Optional[List[str]] = None,
        blacklist: Optional[List[str]] = None,
    ) -> Dict[str, Optional[NastoolPlugin]]:
        """
        Load all discovered plugins.

        Args:
            config: Optional dict of {plugin_name: plugin_config}
            whitelist: Only load these plugin names (None = load all)
            blacklist: Skip these plugin names

        Returns:
            Dict of name -> loaded instance (None if failed)
        """
        blacklist = blacklist or []
        whitelist = whitelist or None

        results = {}

        for name, plugin_class in plugin_registry.classes.items():
            if name in blacklist:
                logger.debug(f"Skipping blacklisted plugin: {name}")
                continue
            if whitelist is not None and name not in whitelist:
                logger.debug(f"Skipping non-whitelisted plugin: {name}")
                continue

            plugin_config = (config or {}).get(name)
            result = load_plugin(plugin_class, plugin_config)
            results[name] = result

        return results

    def load(self, name: str, config: Optional[Dict] = None) -> Optional[NastoolPlugin]:
        """Load a specific plugin by name."""
        plugin_class = plugin_registry.get_class(name)
        if not plugin_class:
            logger.error(f"Plugin not registered: {name}")
            return None
        return load_plugin(plugin_class, config)

    def unload(self, name: str) -> bool:
        """Unload a plugin by name."""
        return unload_plugin(name)

    def reload(self, name: str) -> Optional[NastoolPlugin]:
        """Reload a plugin (unload then load)."""
        self.unload(name)
        return self.load(name)

    # ── Query ───────────────────────────────────────

    def list(
        self,
        include_failed: bool = False,
    ) -> List[PluginMetadata]:
        """
        List all loaded plugins with metadata.

        Args:
            include_failed: Include failed plugins in results

        Returns:
            List of PluginMetadata
        """
        return plugin_registry.list_metadata()

    def get(self, name: str) -> Optional[NastoolPlugin]:
        """Get a loaded plugin instance by name."""
        return plugin_registry.get_instance(name)

    def status(self) -> Dict[str, str]:
        """
        Get status of all plugins.

        Returns:
            Dict mapping plugin name -> status string
        """
        status = {}

        # Loaded
        for name in plugin_registry.instances:
            status[name] = "loaded"

        # Registered but not loaded
        for name in plugin_registry.classes:
            if name not in status:
                status[name] = "registered"

        # Failed
        if True:  # always show if requested
            for name in plugin_registry.failed:
                status[name] = f"failed: {plugin_registry.failed[name]}"

        return status

    # ── Lifecycle ──────────────────────────────────

    def unload_all(self) -> None:
        """Unload all loaded plugins."""
        for name in list(plugin_registry.instances.keys()):
            self.unload(name)

    def reload_all(self) -> Dict[str, Optional[NastoolPlugin]]:
        """Reload all loaded plugins."""
        names = list(plugin_registry.instances.keys())
        self.unload_all()
        return {name: self.load(name) for name in names}
