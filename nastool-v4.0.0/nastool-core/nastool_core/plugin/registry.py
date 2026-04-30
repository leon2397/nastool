"""
plugin/registry.py - Global plugin registry

Tracks all discovered/loaded plugins and provides lookup APIs.
"""

import logging
from typing import Dict, List, Optional, Type
from .base import NastoolPlugin, PluginMetadata

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Singleton registry for all plugins."""

    def __init__(self):
        self._plugins: Dict[str, NastoolPlugin] = {}  # name -> instance
        self._classes: Dict[str, Type[NastoolPlugin]] = {}  # name -> class
        self._failed: Dict[str, str] = {}  # name -> error message

    def register_class(self, plugin_class: Type[NastoolPlugin]) -> bool:
        """
        Register a plugin class (does not instantiate or load it).

        Args:
            plugin_class: A NastoolPlugin subclass

        Returns:
            True if registered successfully
        """
        if not issubclass(plugin_class, NastoolPlugin):
            raise TypeError(
                f"{plugin_class.__name__} must be a subclass of NastoolPlugin"
            )

        name = plugin_class.name
        if name in self._classes:
            logger.warning(f"Plugin '{name}' already registered, overwriting")

        self._classes[name] = plugin_class
        logger.debug(f"Plugin class registered: {name} (v{plugin_class.version})")
        return True

    def unregister(self, name: str) -> bool:
        """Remove a plugin by name. Unloads it first if active."""
        if name in self._plugins:
            self._plugins[name].on_unload()
            del self._plugins[name]
        if name in self._classes:
            del self._classes[name]
        return name in self._plugins or name in self._classes

    def get_class(self, name: str) -> Optional[Type[NastoolPlugin]]:
        """Get a plugin class by name."""
        return self._classes.get(name)

    def get_instance(self, name: str) -> Optional[NastoolPlugin]:
        """Get a loaded plugin instance by name."""
        return self._plugins.get(name)

    @property
    def classes(self) -> Dict[str, Type[NastoolPlugin]]:
        """All registered plugin classes."""
        return dict(self._classes)

    @property
    def instances(self) -> Dict[str, NastoolPlugin]:
        """All loaded plugin instances."""
        return dict(self._plugins)

    @property
    def failed(self) -> Dict[str, str]:
        """Plugins that failed to load (name -> error)."""
        return dict(self._failed)

    def list_metadata(self) -> List[PluginMetadata]:
        """Get metadata for all registered plugins."""
        result = []
        for name, cls in self._classes.items():
            instance = cls()  # temporary instance just for metadata
            result.append(instance.metadata)
        return result

    def clear(self):
        """Unload and remove all plugins."""
        for plugin in self._plugins.values():
            try:
                plugin.on_unload()
            except Exception as e:
                logger.warning(f"Error unloading plugin: {e}")
        self._plugins.clear()
        self._classes.clear()
        self._failed.clear()


# Global singleton
plugin_registry = PluginRegistry()


def register_plugin(plugin_class: Type[NastoolPlugin]) -> bool:
    """
    Convenience function to register a plugin class.

    Usage:
        from nastool_core.plugin import register_plugin

        class MyPlugin(NastoolPlugin):
            name = "my-plugin"
            ...

        register_plugin(MyPlugin)
    """
    return plugin_registry.register_class(plugin_class)
