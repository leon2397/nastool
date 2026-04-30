"""
Threshold Configuration for NASTool

Provides threshold management for different device types and scenarios.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import json
from pathlib import Path


class ThresholdLevel(Enum):
    """Threshold levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    OPTIMAL = "optimal"


@dataclass
class ThresholdValue:
    """Single threshold value"""
    level: ThresholdLevel
    value: float
    description: str = ""


@dataclass
class ThresholdConfig:
    """Configuration for a single check threshold"""
    check_id: str
    warning: float
    critical: float
    optimal: Optional[float] = None
    unit: str = ""
    description: str = ""
    device_specific: Dict[str, Dict[str, float]] = field(default_factory=dict)


class ThresholdConfigManager:
    """
    Threshold configuration manager.

    Provides threshold configurations for different:
    - Device types (RK3588, Jetson, etc.)
    - Usage scenarios (NAS, AI Server, etc.)
    - Check categories
    """

    DEFAULT_THRESHOLDS: Dict[str, ThresholdConfig] = {
        "cpu_temperature": ThresholdConfig(
            check_id="cpu_temperature",
            warning=75.0,
            critical=85.0,
            optimal=50.0,
            unit="°C",
            description="CPU temperature thresholds",
            device_specific={
                "rk3588": {"warning": 70.0, "critical": 80.0, "optimal": 45.0},
                "rk3568": {"warning": 65.0, "critical": 75.0, "optimal": 42.0},
                "jetson_xavier": {"warning": 75.0, "critical": 85.0, "optimal": 50.0},
                "jetson_nano": {"warning": 70.0, "critical": 80.0, "optimal": 45.0},
                "jetson_orin": {"warning": 80.0, "critical": 90.0, "optimal": 55.0},
            }
        ),
        "gpu_temperature": ThresholdConfig(
            check_id="gpu_temperature",
            warning=80.0,
            critical=90.0,
            optimal=55.0,
            unit="°C",
            description="GPU temperature thresholds",
            device_specific={
                "rk3588": {"warning": 75.0, "critical": 85.0, "optimal": 50.0},
                "jetson_xavier": {"warning": 80.0, "critical": 90.0, "optimal": 55.0},
                "jetson_orin": {"warning": 85.0, "critical": 95.0, "optimal": 60.0},
            }
        ),
        "memory_usage": ThresholdConfig(
            check_id="memory_usage",
            warning=80.0,
            critical=95.0,
            optimal=60.0,
            unit="%",
            description="Memory usage thresholds",
            device_specific={
                "nas": {"warning": 85.0, "critical": 95.0, "optimal": 70.0},
                "ai_server": {"warning": 90.0, "critical": 98.0, "optimal": 75.0},
            }
        ),
        "disk_usage": ThresholdConfig(
            check_id="disk_usage",
            warning=85.0,
            critical=95.0,
            optimal=70.0,
            unit="%",
            description="Disk usage thresholds"
        ),
        "cpu_usage": ThresholdConfig(
            check_id="cpu_usage",
            warning=80.0,
            critical=95.0,
            optimal=50.0,
            unit="%",
            description="CPU usage thresholds",
            device_specific={
                "nas": {"warning": 70.0, "critical": 90.0, "optimal": 40.0},
                "ai_server": {"warning": 90.0, "critical": 98.0, "optimal": 70.0},
            }
        ),
        "network_latency": ThresholdConfig(
            check_id="network_latency",
            warning=100.0,
            critical=500.0,
            optimal=50.0,
            unit="ms",
            description="Network latency thresholds"
        ),
        "disk_io_wait": ThresholdConfig(
            check_id="disk_io_wait",
            warning=15.0,
            critical=30.0,
            optimal=5.0,
            unit="%",
            description="Disk I/O wait thresholds",
            device_specific={
                "nas": {"warning": 10.0, "critical": 20.0, "optimal": 3.0},
                "ai_server": {"warning": 20.0, "critical": 40.0, "optimal": 8.0},
            }
        ),
        "npu_temperature": ThresholdConfig(
            check_id="npu_temperature",
            warning=75.0,
            critical=85.0,
            optimal=50.0,
            unit="°C",
            description="NPU temperature thresholds",
            device_specific={
                "rk3588": {"warning": 70.0, "critical": 80.0, "optimal": 45.0},
                "ascend_310": {"warning": 75.0, "critical": 85.0, "optimal": 50.0},
            }
        ),
    }

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize threshold config manager.

        Args:
            config_dir: Configuration directory path
        """
        self.config_dir = Path(config_dir or Path.home() / ".nastool" / "config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._custom_thresholds: Dict[str, ThresholdConfig] = {}
        self._load_custom_thresholds()

    def get_threshold(
        self,
        check_id: str,
        device_type: str = "generic",
        scenario: str = "default"
    ) -> ThresholdConfig:
        """
        Get threshold configuration for a check.

        Args:
            check_id: Check identifier
            device_type: Device type (e.g., "rk3588", "jetson_xavier")
            scenario: Usage scenario (e.g., "nas", "ai_server")

        Returns:
            ThresholdConfig
        """
        threshold = self.DEFAULT_THRESHOLDS.get(check_id)

        if threshold is None:
            return self._create_default_threshold(check_id)

        custom_key = f"{check_id}:{device_type}:{scenario}"
        if custom_key in self._custom_thresholds:
            return self._custom_thresholds[custom_key]

        if device_type != "generic" and check_id in self.DEFAULT_THRESHOLDS:
            device_thresholds = self.DEFAULT_THRESHOLDS[check_id].device_specific
            if device_type in device_thresholds:
                base = self.DEFAULT_THRESHOLDS[check_id]
                device_vals = device_thresholds[device_type]
                return ThresholdConfig(
                    check_id=check_id,
                    warning=device_vals.get("warning", base.warning),
                    critical=device_vals.get("critical", base.critical),
                    optimal=device_vals.get("optimal", base.optimal),
                    unit=base.unit,
                    description=base.description,
                    device_specific={}
                )

        return threshold

    def set_threshold(
        self,
        check_id: str,
        warning: float,
        critical: float,
        device_type: str = "generic",
        scenario: str = "default",
        optimal: Optional[float] = None
    ) -> bool:
        """
        Set custom threshold.

        Args:
            check_id: Check identifier
            warning: Warning threshold
            critical: Critical threshold
            device_type: Device type
            scenario: Usage scenario
            optimal: Optimal threshold

        Returns:
            True if successful
        """
        custom_key = f"{check_id}:{device_type}:{scenario}"

        self._custom_thresholds[custom_key] = ThresholdConfig(
            check_id=check_id,
            warning=warning,
            critical=critical,
            optimal=optimal,
            device_specific={}
        )

        return self._save_custom_thresholds()

    def get_all_thresholds(self) -> Dict[str, ThresholdConfig]:
        """
        Get all threshold configurations.

        Returns:
            Dict of check_id to ThresholdConfig
        """
        return {
            **self.DEFAULT_THRESHOLDS,
            **self._custom_thresholds
        }

    def evaluate_value(
        self,
        check_id: str,
        value: float,
        device_type: str = "generic",
        scenario: str = "default"
    ) -> ThresholdLevel:
        """
        Evaluate a value against thresholds.

        Args:
            check_id: Check identifier
            value: Value to evaluate
            device_type: Device type
            scenario: Usage scenario

        Returns:
            ThresholdLevel
        """
        threshold = self.get_threshold(check_id, device_type, scenario)

        if threshold.optimal is not None and value <= threshold.optimal:
            return ThresholdLevel.OPTIMAL

        if value >= threshold.critical:
            return ThresholdLevel.CRITICAL

        if value >= threshold.warning:
            return ThresholdLevel.WARNING

        return ThresholdLevel.INFO

    def reset_to_default(self, check_id: str) -> bool:
        """
        Reset threshold to default.

        Args:
            check_id: Check identifier

        Returns:
            True if successful
        """
        keys_to_remove = [
            k for k in self._custom_thresholds.keys()
            if k.startswith(f"{check_id}:")
        ]

        for key in keys_to_remove:
            del self._custom_thresholds[key]

        return self._save_custom_thresholds()

    def export_config(self, file_path: str) -> bool:
        """
        Export threshold configuration to file.

        Args:
            file_path: Path to export file

        Returns:
            True if successful
        """
        try:
            config_data = {
                key: {
                    "check_id": config.check_id,
                    "warning": config.warning,
                    "critical": config.critical,
                    "optimal": config.optimal,
                    "unit": config.unit,
                    "description": config.description,
                }
                for key, config in self._custom_thresholds.items()
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            return True

        except Exception:
            return False

    def import_config(self, file_path: str) -> bool:
        """
        Import threshold configuration from file.

        Args:
            file_path: Path to import file

        Returns:
            True if successful
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            for key, data in config_data.items():
                self._custom_thresholds[key] = ThresholdConfig(
                    check_id=data.get("check_id", key),
                    warning=data.get("warning", 70.0),
                    critical=data.get("critical", 85.0),
                    optimal=data.get("optimal"),
                    unit=data.get("unit", ""),
                    description=data.get("description", ""),
                    device_specific={}
                )

            return self._save_custom_thresholds()

        except Exception:
            return False

    def _load_custom_thresholds(self):
        """Load custom thresholds from file"""
        config_file = self.config_dir / "thresholds.json"

        if not config_file.exists():
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            for key, data in config_data.items():
                self._custom_thresholds[key] = ThresholdConfig(
                    check_id=data.get("check_id", key),
                    warning=data.get("warning", 70.0),
                    critical=data.get("critical", 85.0),
                    optimal=data.get("optimal"),
                    unit=data.get("unit", ""),
                    description=data.get("description", ""),
                    device_specific={}
                )

        except Exception:
            pass

    def _save_custom_thresholds(self) -> bool:
        """Save custom thresholds to file"""
        config_file = self.config_dir / "thresholds.json"

        try:
            config_data = {}
            for key, config in self._custom_thresholds.items():
                config_data[key] = {
                    "check_id": config.check_id,
                    "warning": config.warning,
                    "critical": config.critical,
                    "optimal": config.optimal,
                    "unit": config.unit,
                    "description": config.description,
                }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            return True

        except Exception:
            return False

    def _create_default_threshold(self, check_id: str) -> ThresholdConfig:
        """Create a default threshold for unknown checks"""
        return ThresholdConfig(
            check_id=check_id,
            warning=80.0,
            critical=95.0,
            unit="%",
            description=f"Default threshold for {check_id}"
        )


_global_threshold_manager: Optional[ThresholdConfigManager] = None


def get_threshold_manager() -> ThresholdConfigManager:
    """Get global threshold manager instance"""
    global _global_threshold_manager
    if _global_threshold_manager is None:
        _global_threshold_manager = ThresholdConfigManager()
    return _global_threshold_manager


def get_threshold(
    check_id: str,
    device_type: str = "generic",
    scenario: str = "default"
) -> ThresholdConfig:
    """Get threshold configuration (convenience function)"""
    return get_threshold_manager().get_threshold(check_id, device_type, scenario)


def evaluate_threshold(
    check_id: str,
    value: float,
    device_type: str = "generic",
    scenario: str = "default"
) -> ThresholdLevel:
    """Evaluate value against threshold (convenience function)"""
    return get_threshold_manager().evaluate_value(check_id, value, device_type, scenario)


class DynamicThresholdAdjuster:
    """
    Dynamic threshold adjuster based on environmental factors.

    Adjusts thresholds based on:
    - System load
    - Ambient temperature
    - Time of day
    - Historical data
    """

    def __init__(self):
        """Initialize dynamic threshold adjuster"""
        self._load_factors()

    def _load_factors(self):
        """Load adjustment factors from config"""
        self.adjustments = {
            "load_weight": 0.3,
            "ambient_temp_weight": 0.3,
            "uptime_weight": 0.2,
            "time_of_day_weight": 0.2,
        }

    def adjust_threshold(
        self,
        base_threshold: float,
        check_id: str,
        environment: Dict[str, Any]
    ) -> float:
        """
        Adjust threshold based on environment.

        Args:
            base_threshold: Base threshold value
            check_id: Check identifier
            environment: Environment data dict

        Returns:
            Adjusted threshold
        """
        adjustment_factor = self._calculate_adjustment_factor(check_id, environment)
        adjusted = base_threshold * (1 + adjustment_factor)
        return round(adjusted, 1)

    def _calculate_adjustment_factor(
        self,
        check_id: str,
        environment: Dict[str, Any]
    ) -> float:
        """
        Calculate adjustment factor based on environment.

        Returns:
            Adjustment factor (e.g., 0.1 for 10% increase)
        """
        total_adjustment = 0.0

        load_avg = environment.get("load_avg", [0, 0, 0])
        if isinstance(load_avg, list) and len(load_avg) > 0:
            normalized_load = min(load_avg[0] / 4.0, 1.0)
            total_adjustment += normalized_load * self.adjustments.get("load_weight", 0.3)

        ambient_temp = environment.get("ambient_temp")
        if ambient_temp is not None:
            temp_factor = self._calculate_temp_adjustment(ambient_temp, check_id)
            total_adjustment += temp_factor * self.adjustments.get("ambient_temp_weight", 0.3)

        uptime_hours = environment.get("uptime_hours", 0)
        if uptime_hours > 168:
            uptime_factor = min((uptime_hours - 168) / 1000, 0.1)
            total_adjustment += uptime_factor * self.adjustments.get("uptime_weight", 0.2)

        hour = environment.get("hour", 12)
        if 0 <= hour <= 6:
            night_factor = 0.05
            total_adjustment += night_factor * self.adjustments.get("time_of_day_weight", 0.2)

        return max(-0.2, min(total_adjustment, 0.2))

    def _calculate_temp_adjustment(self, ambient_temp: float, check_id: str) -> float:
        """
        Calculate temperature-based adjustment.

        Args:
            ambient_temp: Ambient temperature in Celsius
            check_id: Check identifier

        Returns:
            Adjustment factor
        """
        baseline_temp = 25.0
        temp_diff = ambient_temp - baseline_temp

        if "temperature" in check_id.lower():
            return temp_diff * 0.01
        else:
            return temp_diff * 0.005

    def get_environment_score(self, environment: Dict[str, Any]) -> float:
        """
        Get overall environment health score (0-100).

        Args:
            environment: Environment data

        Returns:
            Score (higher is better)
        """
        score = 100.0

        load_avg = environment.get("load_avg", [0, 0, 0])
        if isinstance(load_avg, list) and len(load_avg) > 0:
            load_penalty = min(load_avg[0] / 4.0, 1.0) * 30
            score -= load_penalty

        ambient_temp = environment.get("ambient_temp")
        if ambient_temp is not None:
            if ambient_temp > 35:
                score -= 20
            elif ambient_temp > 30:
                score -= 10

        uptime_hours = environment.get("uptime_hours", 0)
        if uptime_hours > 720:
            score -= 10

        return max(0, min(score, 100))
