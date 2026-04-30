"""
Config Validator Module for nastool

Validate configuration files and environment variables.

Usage:
    from utils.config_validator import ConfigValidator

    validator = ConfigValidator()
    result = validator.validate_all()
"""

import os
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from nastool_common.config import Config
from nastool_common.logger import get_logger
from nastool_common.exceptions import ConfigurationError

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a single validation check"""

    key: str
    valid: bool
    message: str
    expected: Optional[str] = None
    actual: Optional[Any] = None
    severity: str = "error"  # error, warning, info


class ConfigValidator:
    """
    Validate nastool configuration.

    Checks:
    - Environment variables (NAS_HOST, NAS_PORT, etc.)
    - Config file (config.yaml) existence and format
    - Default values vs actual values
    - Path existence and permissions
    - Network endpoint accessibility

    Example:
        validator = ConfigValidator()
        results = validator.validate_all()

        for r in results:
            status = "[OK]" if r.valid else "[X]"
            print(f"{status} {r.key}: {r.message}")
    """

    # Required configuration keys
    REQUIRED_KEYS = [
        ("NAS_HOST", str, "NAS backend host"),
        ("NAS_PORT", int, "NAS backend port"),
        ("WEB_PORT", int, "Web dashboard port"),
        ("MONITOR_INTERVAL", int, "Monitoring interval"),
    ]

    # Optional configuration keys with defaults
    OPTIONAL_KEYS = [
        ("LOG_LEVEL", str, "Logging level"),
        ("DATA_DIR", str, "Data directory"),
        ("OFFLINE_MODE", bool, "Offline mode"),
    ]

    # Required paths
    REQUIRED_PATHS = [
        ("profiles", "Device profiles directory"),
        ("checks", "Diagnostic checks directory"),
        ("version_db", "Version database directory"),
    ]

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config validator.

        Args:
            config_path: Optional path to config.yaml
        """
        self.config_path = config_path or self._find_config_file()
        self.results: List[ValidationResult] = []

    def _find_config_file(self) -> Optional[str]:
        """Find config.yaml in standard locations"""
        candidates = [
            "config.yaml",
            "nastool/config.yaml",
            os.path.expanduser("~/.nastool/config.yaml"),
            "/etc/nastool/config.yaml",
        ]

        for path in candidates:
            if os.path.exists(path):
                return path

        return None

    def validate_all(self) -> List[ValidationResult]:
        """Run all validation checks"""
        self.results = []

        # Validate environment variables
        self._validate_env_vars()

        # Validate config file
        self._validate_config_file()

        # Validate required paths
        self._validate_paths()

        # Validate network endpoints
        self._validate_network()

        return self.results

    def _validate_env_vars(self) -> None:
        """Validate environment variables"""
        # Required keys
        for key, expected_type, description in self.REQUIRED_KEYS:
            value = getattr(Config, key, None)

            if value is None:
                self.results.append(
                    ValidationResult(
                        key=f"ENV:{key}",
                        valid=False,
                        message=f"Missing required config: {description}",
                        expected=f"{expected_type.__name__}",
                        actual=None,
                        severity="error",
                    )
                )
            elif not isinstance(value, expected_type):
                self.results.append(
                    ValidationResult(
                        key=f"ENV:{key}",
                        valid=False,
                        message=f"Invalid type for {key}",
                        expected=f"{expected_type.__name__}",
                        actual=f"{type(value).__name__} = {value}",
                        severity="error",
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        key=f"ENV:{key}",
                        valid=True,
                        message=f"{description} = {value}",
                        expected=f"{expected_type.__name__}",
                        actual=value,
                        severity="info",
                    )
                )

        # Optional keys
        for key, expected_type, description in self.OPTIONAL_KEYS:
            value = getattr(Config, key, None)

            if value is not None and not isinstance(value, expected_type):
                self.results.append(
                    ValidationResult(
                        key=f"ENV:{key}",
                        valid=False,
                        message=f"Invalid type for {key}",
                        expected=f"{expected_type.__name__}",
                        actual=f"{type(value).__name__} = {value}",
                        severity="warning",
                    )
                )
            elif value is not None:
                self.results.append(
                    ValidationResult(
                        key=f"ENV:{key}",
                        valid=True,
                        message=f"{description} = {value}",
                        severity="info",
                    )
                )

    def _validate_config_file(self) -> None:
        """Validate config.yaml file"""
        if self.config_path is None:
            self.results.append(
                ValidationResult(
                    key="CONFIG:file",
                    valid=True,
                    message="No config.yaml found, using defaults",
                    severity="info",
                )
            )
            return

        if not os.path.exists(self.config_path):
            self.results.append(
                ValidationResult(
                    key="CONFIG:file",
                    valid=False,
                    message=f"Config file not found: {self.config_path}",
                    severity="error",
                )
            )
            return

        # Try to parse YAML
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if config_data is None:
                self.results.append(
                    ValidationResult(
                        key="CONFIG:format",
                        valid=False,
                        message="Config file is empty",
                        severity="warning",
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        key="CONFIG:file",
                        valid=True,
                        message=f"Config file loaded: {self.config_path}",
                        severity="info",
                    )
                )

                # Check for unknown keys
                known_keys = set(k[0] for k in self.REQUIRED_KEYS + self.OPTIONAL_KEYS)
                for key in config_data.keys():
                    key_upper = key.upper()
                    if key_upper not in known_keys:
                        self.results.append(
                            ValidationResult(
                                key=f"CONFIG:unknown:{key}",
                                valid=True,
                                message=f"Unknown config key: {key}",
                                severity="warning",
                            )
                        )

        except yaml.YAMLError as e:
            self.results.append(
                ValidationResult(
                    key="CONFIG:format",
                    valid=False,
                    message=f"Invalid YAML format: {e}",
                    severity="error",
                )
            )
        except Exception as e:
            self.results.append(
                ValidationResult(
                    key="CONFIG:read",
                    valid=False,
                    message=f"Failed to read config file: {e}",
                    severity="error",
                )
            )

    def _validate_paths(self) -> None:
        """Validate required directory paths"""
        base_dir = Path(__file__).parent.parent

        for dir_name, description in self.REQUIRED_PATHS:
            dir_path = base_dir / dir_name

            if not dir_path.exists():
                self.results.append(
                    ValidationResult(
                        key=f"PATH:{dir_name}",
                        valid=False,
                        message=f"{description} not found: {dir_path}",
                        severity="error",
                    )
                )
            elif not dir_path.is_dir():
                self.results.append(
                    ValidationResult(
                        key=f"PATH:{dir_name}",
                        valid=False,
                        message=f"{description} is not a directory: {dir_path}",
                        severity="error",
                    )
                )
            else:
                # Check if readable
                if not os.access(dir_path, os.R_OK):
                    self.results.append(
                        ValidationResult(
                            key=f"PATH:{dir_name}",
                            valid=False,
                            message=f"{description} not readable: {dir_path}",
                            severity="error",
                        )
                    )
                else:
                    self.results.append(
                        ValidationResult(
                            key=f"PATH:{dir_name}",
                            valid=True,
                            message=f"{description}: {dir_path}",
                            severity="info",
                        )
                    )

    def _validate_network(self) -> None:
        """Validate network endpoints"""
        import socket

        # Check NAS backend connectivity
        nas_host = Config.NAS_HOST
        nas_port = Config.NAS_PORT

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((nas_host, nas_port))
            sock.close()

            if result == 0:
                self.results.append(
                    ValidationResult(
                        key="NETWORK:NAS",
                        valid=True,
                        message=f"NAS backend reachable at {nas_host}:{nas_port}",
                        severity="info",
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        key="NETWORK:NAS",
                        valid=False,
                        message=f"NAS backend not reachable at {nas_host}:{nas_port}",
                        severity="warning",
                    )
                )
        except Exception as e:
            self.results.append(
                ValidationResult(
                    key="NETWORK:NAS",
                    valid=False,
                    message=f"Failed to check NAS backend: {e}",
                    severity="warning",
                )
            )

        # Check web dashboard port availability
        web_port = Config.WEB_PORT

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", web_port))
            sock.close()

            if result != 0:
                self.results.append(
                    ValidationResult(
                        key="NETWORK:WEB_PORT",
                        valid=True,
                        message=f"Web dashboard port {web_port} is available",
                        severity="info",
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        key="NETWORK:WEB_PORT",
                        valid=True,
                        message=f"Web dashboard already running on port {web_port}",
                        severity="info",
                    )
                )
        except Exception as e:
            self.results.append(
                ValidationResult(
                    key="NETWORK:WEB_PORT",
                    valid=False,
                    message=f"Failed to check web port: {e}",
                    severity="warning",
                )
            )

    def print_report(self) -> None:
        """Print validation report to console"""
        print("\n📋 Configuration Validation Report")
        print("=" * 50)

        errors = [r for r in self.results if r.severity == "error"]
        warnings = [r for r in self.results if r.severity == "warning"]
        infos = [r for r in self.results if r.severity == "info"]

        for result in self.results:
            if result.valid:
                icon = "[OK]"
            elif result.severity == "error":
                icon = "[X]"
            elif result.severity == "warning":
                icon = "[!]"
            else:
                icon = "ℹ"

            print(f"{icon} {result.key}: {result.message}")

            if result.expected and not result.valid:
                print(f"   Expected: {result.expected}")
                print(f"   Actual: {result.actual}")

        print("\n" + "=" * 50)
        print(f"📊 Summary: {len(infos)} OK, {len(warnings)} warnings, {len(errors)} errors")

        if errors:
            print("\n[X] Configuration has errors. Please fix before running diagnostics.")
        elif warnings:
            print(
                "\n[!] Configuration has warnings. Diagnostics may work but some features may be limited."
            )
        else:
            print("\n[OK] Configuration is valid!")

    def is_valid(self) -> bool:
        """Check if configuration is valid (no errors)"""
        return not any(r.severity == "error" and not r.valid for r in self.results)


def validate_config() -> Tuple[bool, List[ValidationResult]]:
    """
    Convenience function to validate configuration.

    Returns:
        Tuple of (is_valid, results)
    """
    validator = ConfigValidator()
    results = validator.validate_all()
    return validator.is_valid(), results


if __name__ == "__main__":
    # Standalone validation
    validator = ConfigValidator()
    validator.validate_all()
    validator.print_report()

    sys.exit(0 if validator.is_valid() else 1)
