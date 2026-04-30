"""
plugin/__init__.py - NASTool Plugin System

Allows third-party extensions to register custom checks, adapters, and reporters.

Architecture:
    - Plugin framework lives in nastool-core (lowest dependency layer)
    - Plugin loading/management lives in nastool-cli
    - Plugins can only register into checks/registry and adapters/registry
    - Plugins MUST NOT import from nastool-cli, nastool-reporters, nastool-fixes

Usage (plugin author):
    from nastool_core.plugin import NastoolPlugin, register_plugin

    class MyPlugin(NastoolPlugin):
        name = "my-plugin"
        version = "1.0.0"

        def register_checks(self):
            return [MyCustomCheck]

        def register_adapters(self):
            return [("my-device", MyDeviceAdapter)]

    register_plugin(MyPlugin)

Usage (CLI / entry point):
    from nastool_core.plugin import PluginManager

    mgr = PluginManager()
    mgr.discover_entrypoints()   # pip-installed plugins
    mgr.discover_directory("~/.nastool/plugins")
    mgr.load_all()
"""

from .base import NastoolPlugin, PluginMetadata
from .registry import PluginRegistry, plugin_registry, register_plugin
from .loader import (
    discover_entrypoints,
    discover_directory,
    load_plugin,
    unload_plugin,
)
from .manager import PluginManager

__all__ = [
    "NastoolPlugin",
    "PluginMetadata",
    "PluginRegistry",
    "plugin_registry",
    "register_plugin",
    "discover_entrypoints",
    "discover_directory",
    "load_plugin",
    "unload_plugin",
    "PluginManager",
]
