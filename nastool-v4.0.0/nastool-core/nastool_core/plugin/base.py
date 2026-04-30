"""
plugin/base.py - Plugin base class and metadata

Every NASTool plugin must inherit from NastoolPlugin and implement
at least one of: register_checks(), register_adapters().
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple, Type, Optional, Dict, Any


@dataclass
class PluginMetadata:
    """Plugin descriptor."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    homepage: str = ""
    min_nastool_version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)


class NastoolPlugin(ABC):
    """
    Abstract base class for all NASTool plugins.

    A plugin can contribute:
    - Custom checks (registered via checks/registry)
    - Custom adapters (registered via adapters/registry)

    Lifecycle:
    1. Plugin class instantiated
    2. on_load(config) called with optional plugin config
    3. register_checks() / register_adapters() called
    4. Plugin is active until on_unload() is called
    """

    # Subclasses SHOULD override these
    name: str = "unnamed-plugin"
    version: str = "0.1.0"
    description: str = ""
    author: str = ""

    def __init__(self):
        self._loaded = False
        self._config: Dict[str, Any] = {}

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
        )

    @property
    def loaded(self) -> bool:
        return self._loaded

    # ── Lifecycle hooks ────────────────────────────────────

    def on_load(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Called when the plugin is loaded.
        Override to initialize resources, read config, etc.
        """
        self._config = config or {}
        self._loaded = True

    def on_unload(self) -> None:
        """
        Called when the plugin is unloaded.
        Override to clean up resources.
        """
        self._loaded = False

    # ── Extension points ──────────────────────────────────

    def register_checks(self) -> List[Type]:
        """
        Return a list of Check subclasses to register.
        Each class must inherit from nastool_core.checks.base.Check.

        Example:
            from nastool_core.checks.base import Check
            class MyCheck(Check):
                check_id = "my_check"
                ...
            return [MyCheck]
        """
        return []

    def register_adapters(self) -> List[Tuple[str, type]]:
        """
        Return a list of (name, AdapterClass) tuples to register.
        Each AdapterClass must inherit from nastool_adapters.base.BaseAdapter.

        Example:
            return [("my-device", MyDeviceAdapter)]
        """
        return []

    def register_commands(self) -> List[Dict[str, Any]]:
        """
        Return a list of CLI command descriptors for extension commands.

        Each descriptor is a dict with:
        - name: command name (e.g. "scan")
        - help: short help text
        - handler: async function(context) -> None

        Example:
            return [{
                "name": "scan",
                "help": "Run custom scan",
                "handler": self._handle_scan,
            }]
        """
        return []

    # ── Optional hooks ────────────────────────────────────

    def on_check_result(self, result: Any) -> None:
        """
        Hook called after each check completes.
        Override to react to check results (e.g. trigger alerts).
        """
        pass

    def on_diagnosis_complete(self, summary: Any) -> None:
        """
        Hook called after a full diagnosis run completes.
        Override to react to the full summary.
        """
        pass
