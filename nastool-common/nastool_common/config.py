"""
nastool Configuration Management

Centralized configuration with environment variable support.
All hardcoded values should be moved here.

Usage:
    from config import Config

    host = Config.NAS_HOST
    port = Config.NAS_PORT
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """
    nastool configuration management.

    Priority: Environment Variable > config.yaml > Default
    """

    # ==================== NAS Backend ====================
    NAS_HOST: str = os.getenv("NASTOOL_NAS_HOST", "120.77.249.3")
    NAS_PORT: int = int(os.getenv("NASTOOL_NAS_PORT", "8000"))
    NAS_TIMEOUT: int = int(os.getenv("NASTOOL_NAS_TIMEOUT", "30"))
    NAS_REGISTER_ENDPOINT: str = "/api/devices/register"

    @classmethod
    def nas_url(cls) -> str:
        """Get NAS backend URL."""
        return f"http://{cls.NAS_HOST}:{cls.NAS_PORT}"

    # ==================== Web Dashboard ====================
    WEB_HOST: str = os.getenv("NASTOOL_WEB_HOST", "0.0.0.0")
    WEB_PORT: int = int(os.getenv("NASTOOL_WEB_PORT", "8080"))
    WEB_DEBUG: bool = os.getenv("NASTOOL_WEB_DEBUG", "false").lower() == "true"

    @classmethod
    def web_url(cls) -> str:
        """Get Web Dashboard URL."""
        return f"http://{cls.WEB_HOST}:{cls.WEB_PORT}"

    # ==================== Monitoring Daemon ====================
    MONITOR_INTERVAL: int = int(os.getenv("NASTOOL_MONITOR_INTERVAL", "60"))
    MONITOR_ENABLED: bool = os.getenv("NASTOOL_MONITOR_ENABLED", "true").lower() == "true"
    MONITOR_HISTORY_SIZE: int = int(os.getenv("NASTOOL_MONITOR_HISTORY_SIZE", "100"))

    # ==================== Storage Paths ====================
    DEFAULT_SCAN_PATH: Path = Path(os.getenv("NASTOOL_SCAN_PATH", "/nas"))
    DEFAULT_MEDIA_PATH: Path = Path(os.getenv("NASTOOL_MEDIA_PATH", "/nas/media"))
    DEFAULT_CACHE_PATH: Path = Path(os.getenv("NASTOOL_CACHE_PATH", "/tmp/nastool"))

    # ==================== Diagnostic Settings ====================
    CHECK_TIMEOUT: int = int(os.getenv("NASTOOL_CHECK_TIMEOUT", "10"))
    BENCHMARK_SIZE_MB: int = int(os.getenv("NASTOOL_BENCHMARK_SIZE", "100"))
    MAX_WORKERS: int = int(os.getenv("NASTOOL_MAX_WORKERS", "4"))

    # ==================== Thresholds ====================
    # Disk space thresholds (GB)
    DISK_WARNING_GB: int = int(os.getenv("NASTOOL_DISK_WARNING_GB", "50"))
    DISK_CRITICAL_GB: int = int(os.getenv("NASTOOL_DISK_CRITICAL_GB", "10"))

    # Memory thresholds (percentage)
    MEMORY_WARNING_PERCENT: int = int(os.getenv("NASTOOL_MEMORY_WARNING_PERCENT", "80"))
    MEMORY_CRITICAL_PERCENT: int = int(os.getenv("NASTOOL_MEMORY_CRITICAL_PERCENT", "95"))

    # Temperature thresholds (Celsius)
    TEMP_WARNING_C: int = int(os.getenv("NASTOOL_TEMP_WARNING_C", "70"))
    TEMP_CRITICAL_C: int = int(os.getenv("NASTOOL_TEMP_CRITICAL_C", "85"))

    # Write speed thresholds (MB/s)
    WRITE_SPEED_WARNING: int = int(os.getenv("NASTOOL_WRITE_SPEED_WARNING", "50"))
    WRITE_SPEED_CRITICAL: int = int(os.getenv("NASTOOL_WRITE_SPEED_CRITICAL", "10"))

    # ==================== Logging ====================
    LOG_LEVEL: str = os.getenv("NASTOOL_LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # ==================== Version Database ====================
    VERSION_DB_URL: str = os.getenv(
        "NASTOOL_VERSION_DB_URL",
        "https://raw.githubusercontent.com/leon2397/qizhiainas/main/arm/nastool/version_db/versions.json",
    )
    VERSION_DB_CACHE_HOURS: int = int(os.getenv("NASTOOL_VERSION_DB_CACHE_HOURS", "24"))

    # ==================== Language ====================
    LANGUAGE: str = os.getenv("NASTOOL_LANG", "en")

    # ==================== Paths ====================
    PROJECT_ROOT: Path = Path(__file__).parent
    DATA_DIR: Path = Path(os.getenv("NASTOOL_DATA_DIR", str(PROJECT_ROOT / "data")))
    PROFILES_DIR: Path = PROJECT_ROOT / "profiles"
    VERSION_DB_DIR: Path = PROJECT_ROOT / "version_db"

    @classmethod
    def ensure_paths(cls) -> None:
        """Ensure all required directories exist."""
        cls.DEFAULT_CACHE_PATH.mkdir(parents=True, exist_ok=True)
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_from_yaml(cls, path: Optional[Path] = None) -> None:
        """
        Load configuration from YAML file.

        Args:
            path: Path to config.yaml. Default: ./config.yaml
        """
        import yaml

        if path is None:
            path = cls.PROJECT_ROOT / "config.yaml"

        if not path.exists():
            return

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Override defaults with YAML values (env vars take precedence)
        for key, value in data.items():
            if not os.getenv(f"NASTOOL_{key.upper()}"):
                if hasattr(cls, key.upper()):
                    setattr(cls, key.upper(), value)

    @classmethod
    def to_dict(cls) -> dict:
        """Export configuration as dictionary."""
        return {
            "nas": {
                "host": cls.NAS_HOST,
                "port": cls.NAS_PORT,
                "url": cls.nas_url(),
            },
            "web": {
                "host": cls.WEB_HOST,
                "port": cls.WEB_PORT,
                "url": cls.web_url(),
            },
            "monitor": {
                "interval": cls.MONITOR_INTERVAL,
                "enabled": cls.MONITOR_ENABLED,
            },
            "paths": {
                "scan": str(cls.DEFAULT_SCAN_PATH),
                "media": str(cls.DEFAULT_MEDIA_PATH),
                "cache": str(cls.DEFAULT_CACHE_PATH),
            },
            "thresholds": {
                "disk_warning_gb": cls.DISK_WARNING_GB,
                "disk_critical_gb": cls.DISK_CRITICAL_GB,
                "memory_warning_percent": cls.MEMORY_WARNING_PERCENT,
                "temp_warning_c": cls.TEMP_WARNING_C,
            },
            "log_level": cls.LOG_LEVEL,
            "language": cls.LANGUAGE,
        }


# Initialize on import
Config.ensure_paths()
