# -*- coding: utf-8 -*-
"""
core/config_loader.py — 检测项配置加载器
从 YAML 文件读取阈值、超时、权重等配置
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List


# ══════════════════════════════════════════════════════════════════
# 默认配置（YAML 不存在时使用）
# ══════════════════════════════════════════════════════════════════

DEFAULT_CONFIG = {
    "system": {
        "python": {"min_version": "3.8", "recommended_version": "3.11"},
        "memory": {
            "min_mb": 1024,
            "recommended_mb": 4096,
            "warning_percent": 85,
            "critical_percent": 95,
        },
        "cpu": {
            "warning_percent": 80,
            "critical_percent": 95,
            "warning_temp": 70,
            "critical_temp": 85,
        },
        "disk": {"warning_percent": 80, "critical_percent": 95, "min_free_gb": 10},
    },
    "storage": {
        "smart": {
            "attributes": {
                "reallocated_sectors": {"warning": 10, "critical": 100},
                "pending_sectors": {"warning": 10, "critical": 100},
                "temperature": {"warning": 55, "critical": 70},
            }
        },
        "temperature": {"warning": 55, "critical": 70},
        "raid": {},
    },
    "network": {
        "bandwidth": {"speedtest_timeout": 30, "min_download_mbps": 10},
        "dns": {"timeout_seconds": 5},
        "interface": {"min_speed_mbps": 100},
    },
    "security": {
        "login_failures": {"hours": 24, "warning_threshold": 10, "critical_threshold": 50},
        "ssl": {"warning_days": 30, "critical_days": 7},
        "ssh": {"permit_root_login": False, "password_authentication": False},
    },
    "nas": {
        "ups": {"low_battery_percent": 20, "critical_battery_percent": 10},
        "share": {"warning_usage_percent": 80, "critical_usage_percent": 95},
    },
    "ai": {
        "gpu": {"warning_temp": 80, "critical_temp": 90},
    },
    "scoring": {
        "weights": {"system": 20, "storage": 25, "network": 15, "security": 25, "nas": 10, "ai": 5},
    },
    "timeouts": {
        "ssh_connect": 10,
        "ssh_command": 30,
        "http_request": 10,
    },
}


# ══════════════════════════════════════════════════════════════════
# 配置加载器
# ══════════════════════════════════════════════════════════════════


class ConfigLoader:
    """配置加载器"""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._config:
            self._load_config()

    def _load_config(self):
        """加载配置文件"""
        # 查找配置文件
        config_paths = [
            Path(__file__).parent.parent / "config" / "checks.yaml",
            Path.home() / ".nastool" / "checks.yaml",
            Path("/etc/nastool/checks.yaml"),
        ]

        config_file = None
        for path in config_paths:
            if path.exists():
                config_file = path
                break

        if config_file:
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()

    def reload(self):
        """重新加载配置"""
        self._config = {}
        self._load_config()

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点分隔路径）

        Args:
            key: 配置键，如 "system.memory.warning_percent"
            default: 默认值

        Returns:
            配置值
        """
        parts = key.split(".")
        value = self._config

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取整个配置节

        Args:
            section: 节名称，如 "system"

        Returns:
            配置字典
        """
        return self._config.get(section, {})

    @property
    def system(self) -> "SystemConfig":
        """系统配置"""
        return SystemConfig(self._config.get("system", {}))

    @property
    def storage(self) -> "StorageConfig":
        """存储配置"""
        return StorageConfig(self._config.get("storage", {}))

    @property
    def network(self) -> "NetworkConfig":
        """网络配置"""
        return NetworkConfig(self._config.get("network", {}))

    @property
    def security(self) -> "SecurityConfig":
        """安全配置"""
        return SecurityConfig(self._config.get("security", {}))

    @property
    def nas(self) -> "NASConfig":
        """NAS 配置"""
        return NASConfig(self._config.get("nas", {}))

    @property
    def ai(self) -> "AIConfig":
        """AI 配置"""
        return AIConfig(self._config.get("ai", {}))

    @property
    def scoring(self) -> "ScoringConfig":
        """评分配置"""
        return ScoringConfig(self._config.get("scoring", {}))

    @property
    def timeouts(self) -> "TimeoutConfig":
        """超时配置"""
        return TimeoutConfig(self._config.get("timeouts", {}))


# ══════════════════════════════════════════════════════════════════
# 各模块配置类
# ══════════════════════════════════════════════════════════════════


class SystemConfig:
    """系统配置"""

    def __init__(self, data: Dict):
        self._data = data

    @property
    def python_min_version(self) -> str:
        return self._data.get("python", {}).get("min_version", "3.8")

    @property
    def python_recommended_version(self) -> str:
        return self._data.get("python", {}).get("recommended_version", "3.11")

    @property
    def memory_min_mb(self) -> int:
        return self._data.get("memory", {}).get("min_mb", 1024)

    @property
    def memory_recommended_mb(self) -> int:
        return self._data.get("memory", {}).get("recommended_mb", 4096)

    @property
    def memory_warning_percent(self) -> int:
        return self._data.get("memory", {}).get("warning_percent", 85)

    @property
    def memory_critical_percent(self) -> int:
        return self._data.get("memory", {}).get("critical_percent", 95)

    @property
    def cpu_warning_percent(self) -> int:
        return self._data.get("cpu", {}).get("warning_percent", 80)

    @property
    def cpu_critical_percent(self) -> int:
        return self._data.get("cpu", {}).get("critical_percent", 95)

    @property
    def cpu_warning_temp(self) -> int:
        return self._data.get("cpu", {}).get("warning_temp", 70)

    @property
    def cpu_critical_temp(self) -> int:
        return self._data.get("cpu", {}).get("critical_temp", 85)

    @property
    def disk_warning_percent(self) -> int:
        return self._data.get("disk", {}).get("warning_percent", 80)

    @property
    def disk_critical_percent(self) -> int:
        return self._data.get("disk", {}).get("critical_percent", 95)


class StorageConfig:
    """存储配置"""

    def __init__(self, data: Dict):
        self._data = data

    @property
    def temp_warning(self) -> int:
        return self._data.get("temperature", {}).get("warning", 55)

    @property
    def temp_critical(self) -> int:
        return self._data.get("temperature", {}).get("critical", 70)

    @property
    def smart_reallocated_warning(self) -> int:
        return (
            self._data.get("smart", {})
            .get("attributes", {})
            .get("reallocated_sectors", {})
            .get("warning", 10)
        )

    @property
    def smart_reallocated_critical(self) -> int:
        return (
            self._data.get("smart", {})
            .get("attributes", {})
            .get("reallocated_sectors", {})
            .get("critical", 100)
        )

    @property
    def smart_pending_warning(self) -> int:
        return (
            self._data.get("smart", {})
            .get("attributes", {})
            .get("pending_sectors", {})
            .get("warning", 10)
        )

    @property
    def smart_pending_critical(self) -> int:
        return (
            self._data.get("smart", {})
            .get("attributes", {})
            .get("pending_sectors", {})
            .get("critical", 100)
        )


class NetworkConfig:
    """网络配置"""

    def __init__(self, data: Dict):
        self._data = data

    @property
    def dns_timeout(self) -> int:
        return self._data.get("dns", {}).get("timeout_seconds", 5)

    @property
    def dns_servers(self) -> List[Dict]:
        return self._data.get("dns", {}).get("servers", [])

    @property
    def min_speed_mbps(self) -> int:
        return self._data.get("interface", {}).get("min_speed_mbps", 100)

    @property
    def common_ports(self) -> List[int]:
        return self._data.get("port_scan", {}).get("common_ports", [22, 80, 443, 8000])


class SecurityConfig:
    """安全配置"""

    def __init__(self, data: Dict):
        self._data = data

    @property
    def login_failure_hours(self) -> int:
        return self._data.get("login_failures", {}).get("hours", 24)

    @property
    def login_failure_warning(self) -> int:
        return self._data.get("login_failures", {}).get("warning_threshold", 10)

    @property
    def login_failure_critical(self) -> int:
        return self._data.get("login_failures", {}).get("critical_threshold", 50)

    @property
    def ssl_warning_days(self) -> int:
        return self._data.get("ssl", {}).get("warning_days", 30)

    @property
    def ssl_critical_days(self) -> int:
        return self._data.get("ssl", {}).get("critical_days", 7)

    @property
    def ssh_permit_root(self) -> bool:
        return self._data.get("ssh", {}).get("permit_root_login", False)

    @property
    def ssh_password_auth(self) -> bool:
        return self._data.get("ssh", {}).get("password_authentication", False)


class NASConfig:
    """NAS 配置"""

    def __init__(self, data: Dict):
        self._data = data

    @property
    def ups_low_battery(self) -> int:
        return self._data.get("ups", {}).get("low_battery_percent", 20)

    @property
    def ups_critical_battery(self) -> int:
        return self._data.get("ups", {}).get("critical_battery_percent", 10)

    @property
    def share_warning_percent(self) -> int:
        return self._data.get("share", {}).get("warning_usage_percent", 80)

    @property
    def share_critical_percent(self) -> int:
        return self._data.get("share", {}).get("critical_usage_percent", 95)


class AIConfig:
    """AI 配置"""

    def __init__(self, data: Dict):
        self._data = data

    @property
    def gpu_warning_temp(self) -> int:
        return self._data.get("gpu", {}).get("warning_temp", 80)

    @property
    def gpu_critical_temp(self) -> int:
        return self._data.get("gpu", {}).get("critical_temp", 90)

    @property
    def cuda_min_version(self) -> str:
        return self._data.get("cuda", {}).get("min_version", "11.0")


class ScoringConfig:
    """评分配置"""

    def __init__(self, data: Dict):
        self._data = data

    @property
    def weights(self) -> Dict[str, int]:
        return self._data.get(
            "weights",
            {"system": 20, "storage": 25, "network": 15, "security": 25, "nas": 10, "ai": 5},
        )

    @property
    def penalties(self) -> Dict[str, int]:
        return self._data.get("penalties", {})

    def get_penalty(self, key: str) -> int:
        """获取扣分值"""
        return self.penalties.get(key, 10)


class TimeoutConfig:
    """超时配置"""

    def __init__(self, data: Dict):
        self._data = data

    @property
    def ssh_connect(self) -> int:
        return self._data.get("ssh_connect", 10)

    @property
    def ssh_command(self) -> int:
        return self._data.get("ssh_command", 30)

    @property
    def http_request(self) -> int:
        return self._data.get("http_request", 10)

    @property
    def dns_resolve(self) -> int:
        return self._data.get("dns_resolve", 5)

    @property
    def port_scan(self) -> int:
        return self._data.get("port_scan", 5)

    @property
    def speed_test(self) -> int:
        return self._data.get("speed_test", 30)


# ══════════════════════════════════════════════════════════════════
# 全局实例
# ══════════════════════════════════════════════════════════════════


def get_config() -> ConfigLoader:
    """获取配置加载器实例"""
    return ConfigLoader()


def reload_config():
    """重新加载配置"""
    get_config().reload()
