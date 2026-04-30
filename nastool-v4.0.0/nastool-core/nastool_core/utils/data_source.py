"""
Data Source Abstraction Layer for NASTool

Provides a unified interface for different data sources in detection.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from enum import Enum
import time


class DataSourceType(Enum):
    """Types of data sources"""
    FILE = "file"
    COMMAND = "command"
    SOCKET = "socket"
    API = "api"
    SENSOR = "sensor"
    SYSTEM = "system"


class DataSourceStatus(Enum):
    """Status of data source"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class DataSourceResult:
    """Result from a data source read operation"""
    success: bool
    value: Any = None
    error: Optional[str] = None
    timestamp: float = 0.0
    latency_ms: float = 0.0
    source_name: str = ""


@dataclass
class DataSourceConfig:
    """Configuration for a data source"""
    name: str
    source_type: DataSourceType
    priority: int = 100
    timeout: float = 5.0
    retry_count: int = 3
    retry_delay: float = 1.0
    cache_ttl: float = 0.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataSource(ABC):
    """
    Abstract base class for data sources.

    Subclasses must implement the _read method to provide
    platform-specific data reading functionality.
    """

    def __init__(self, config: DataSourceConfig):
        """
        Initialize data source.

        Args:
            config: DataSource configuration
        """
        self.config = config
        self._last_value: Optional[Any] = None
        self._last_read_time: float = 0.0
        self._cache: Optional[DataSourceResult] = None

    @property
    def name(self) -> str:
        """Get data source name"""
        return self.config.name

    @property
    def source_type(self) -> DataSourceType:
        """Get data source type"""
        return self.config.source_type

    @property
    def priority(self) -> int:
        """Get priority (lower is higher priority)"""
        return self.config.priority

    def is_available(self) -> bool:
        """
        Check if data source is currently available.

        Returns:
            True if available
        """
        if not self.config.enabled:
            return False
        return self._check_availability()

    @abstractmethod
    def _check_availability(self) -> bool:
        """
        Check if this data source is available on the system.

        Returns:
            True if available
        """
        pass

    @abstractmethod
    def _read(self) -> Any:
        """
        Read data from the source.

        Returns:
            Data value

        Raises:
            Exception: If read fails
        """
        pass

    def read(self) -> DataSourceResult:
        """
        Read data with caching and error handling.

        Returns:
            DataSourceResult
        """
        start_time = time.time()

        if self._cache is not None and self.config.cache_ttl > 0:
            if start_time - self._cache.timestamp < self.config.cache_ttl:
                return self._cache

        try:
            value = self._read()
            self._last_value = value
            self._last_read_time = start_time

            result = DataSourceResult(
                success=True,
                value=value,
                timestamp=start_time,
                latency_ms=(time.time() - start_time) * 1000,
                source_name=self.name
            )

            if self.config.cache_ttl > 0:
                self._cache = result

            return result

        except Exception as e:
            return DataSourceResult(
                success=False,
                error=str(e),
                timestamp=start_time,
                latency_ms=(time.time() - start_time) * 1000,
                source_name=self.name
            )

    def get_last_value(self) -> Optional[Any]:
        """Get last successful read value"""
        return self._last_value

    def clear_cache(self):
        """Clear cached value"""
        self._cache = None


class FileDataSource(DataSource):
    """Data source that reads from a file"""

    def __init__(self, name: str, file_path: str, priority: int = 100, timeout: float = 5.0):
        config = DataSourceConfig(
            name=name,
            source_type=DataSourceType.FILE,
            priority=priority,
            timeout=timeout,
            metadata={"file_path": file_path}
        )
        super().__init__(config)
        self.file_path = file_path

    def _check_availability(self) -> bool:
        import os
        return os.path.exists(self.file_path)

    def _read(self) -> str:
        with open(self.file_path, 'r') as f:
            return f.read()


class CommandDataSource(DataSource):
    """Data source that executes a command"""

    def __init__(self, name: str, command: str, priority: int = 100, timeout: float = 10.0):
        config = DataSourceConfig(
            name=name,
            source_type=DataSourceType.COMMAND,
            priority=priority,
            timeout=timeout,
            metadata={"command": command}
        )
        super().__init__(config)
        self.command = command

    def _check_availability(self) -> bool:
        import shutil
        cmd = self.command.split()[0]
        return shutil.which(cmd) is not None

    def _read(self) -> str:
        import subprocess
        result = subprocess.run(
            self.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.config.timeout
        )
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {result.stderr}")
        return result.stdout.strip()


class ProcDataSource(DataSource):
    """Data source that reads from /proc filesystem"""

    def __init__(self, name: str, proc_path: str, priority: int = 100):
        config = DataSourceConfig(
            name=name,
            source_type=DataSourceType.SYSTEM,
            priority=priority,
            metadata={"proc_path": proc_path}
        )
        super().__init__(config)
        self.proc_path = proc_path

    def _check_availability(self) -> bool:
        import os
        return os.path.exists(self.proc_path)

    def _read(self) -> str:
        with open(self.proc_path, 'r') as f:
            return f.read()


class SysClassDataSource(DataSource):
    """Data source that reads from /sys/class"""

    def __init__(self, name: str, sys_path: str, priority: int = 100):
        config = DataSourceConfig(
            name=name,
            source_type=DataSourceType.SYSTEM,
            priority=priority,
            metadata={"sys_path": sys_path}
        )
        super().__init__(config)
        self.sys_path = sys_path

    def _check_availability(self) -> bool:
        import os
        return os.path.exists(self.sys_path)

    def _read(self) -> str:
        with open(self.sys_path, 'r') as f:
            return f.read().strip()


class DataSourceRegistry:
    """
    Registry for managing data sources.

    Provides a centralized way to register and access data sources.
    """

    def __init__(self):
        self._sources: Dict[str, DataSource] = {}

    def register(self, source: DataSource) -> None:
        """
        Register a data source.

        Args:
            source: DataSource to register
        """
        self._sources[source.name] = source

    def unregister(self, name: str) -> None:
        """
        Unregister a data source.

        Args:
            name: Name of data source to unregister
        """
        if name in self._sources:
            del self._sources[name]

    def get(self, name: str) -> Optional[DataSource]:
        """
        Get a data source by name.

        Args:
            name: Name of data source

        Returns:
            DataSource or None
        """
        return self._sources.get(name)

    def get_all(self) -> List[DataSource]:
        """
        Get all registered data sources.

        Returns:
            List of DataSource
        """
        return list(self._sources.values())

    def get_available(self) -> List[DataSource]:
        """
        Get all available data sources.

        Returns:
            List of available DataSource
        """
        return [s for s in self._sources.values() if s.is_available()]

    def get_by_type(self, source_type: DataSourceType) -> List[DataSource]:
        """
        Get data sources by type.

        Args:
            source_type: Type to filter by

        Returns:
            List of matching DataSource
        """
        return [s for s in self._sources.values() if s.source_type == source_type]


_global_registry = DataSourceRegistry()


def get_data_source_registry() -> DataSourceRegistry:
    """Get global data source registry"""
    return _global_registry


class FusionMethod(Enum):
    """Data fusion methods"""
    AVERAGE = "average"
    WEIGHTED_AVERAGE = "weighted_average"
    MEDIAN = "median"
    MAX = "max"
    MIN = "min"
    VOTE = "vote"
    MOST_RECENT = "most_recent"
    MOST_RELIABLE = "most_reliable"


@dataclass
class FusionConfig:
    """Configuration for data fusion"""
    method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE
    consistency_threshold: float = 0.2
    min_sources: int = 1
    max_age_seconds: float = 60.0
    outlier_removal: bool = True
    outlier_threshold: float = 2.0


class DataFusionEngine:
    """
    Data fusion engine for combining data from multiple sources.

    Features:
    - Multiple fusion methods
    - Outlier detection and removal
    - Consistency checking
    - Confidence scoring
    """

    def __init__(self, config: Optional[FusionConfig] = None):
        """
        Initialize fusion engine.

        Args:
            config: Fusion configuration
        """
        self.config = config or FusionConfig()

    def fuse(
        self,
        results: List[DataSourceResult],
        weights: Optional[Dict[str, float]] = None
    ) -> "FusionOutput":
        """
        Fuse data from multiple sources.

        Args:
            results: List of DataSourceResult
            weights: Optional weights for each source (by name)

        Returns:
            FusionOutput with fused value and metadata
        """
        if not results:
            return FusionOutput(
                success=False,
                error="No data sources provided"
            )

        successful_results = [r for r in results if r.success]

        if len(successful_results) < self.config.min_sources:
            return FusionOutput(
                success=False,
                error=f"Insufficient data sources: {len(successful_results)}/{self.config.min_sources}"
            )

        values = [r.value for r in successful_results]
        source_names = [r.source_name for r in successful_results]
        timestamps = [r.timestamp for r in successful_results]

        if self.config.outlier_removal and len(values) > 2:
            values, successful_results = self._remove_outliers(values, successful_results)

        if not values:
            return FusionOutput(
                success=False,
                error="All values removed as outliers"
            )

        method = self.config.method

        if method == FusionMethod.AVERAGE:
            fused_value = self._average(values)
            confidence = 0.7 if len(values) > 1 else 0.5
        elif method == FusionMethod.WEIGHTED_AVERAGE:
            fused_value = self._weighted_average(values, weights, source_names)
            confidence = 0.85 if len(values) > 1 else 0.6
        elif method == FusionMethod.MEDIAN:
            fused_value = self._median(values)
            confidence = 0.75
        elif method == FusionMethod.MAX:
            fused_value = max(values)
            confidence = 0.6
        elif method == FusionMethod.MIN:
            fused_value = min(values)
            confidence = 0.6
        elif method == FusionMethod.VOTE:
            fused_value = self._vote(values)
            confidence = 0.7
        elif method == FusionMethod.MOST_RECENT:
            fused_value, confidence = self._most_recent(values, timestamps)
        elif method == FusionMethod.MOST_RELIABLE:
            fused_value, confidence = self._most_reliable(successful_results, weights)
        else:
            fused_value = self._average(values)
            confidence = 0.6

        deviation = self._calculate_deviation(values)
        consistency = self._check_consistency(values)

        return FusionOutput(
            success=True,
            fused_value=fused_value,
            confidence=confidence,
            sources_used=source_names,
            method=method.value,
            deviation=deviation,
            is_consistent=consistency,
            values_count=len(values)
        )

    def _remove_outliers(
        self,
        values: List[Any],
        results: List[DataSourceResult]
    ) -> tuple:
        """Remove outliers from values"""
        try:
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            if len(numeric_values) < 3:
                return values, results

            mean_val = sum(numeric_values) / len(numeric_values)
            variance = sum((v - mean_val) ** 2 for v in numeric_values) / len(numeric_values)
            std_dev = variance ** 0.5

            if std_dev == 0:
                return values, results

            threshold = self.config.outlier_threshold * std_dev

            filtered_values = []
            filtered_results = []
            for v, r in zip(values, results):
                if isinstance(v, (int, float)):
                    if abs(v - mean_val) <= threshold:
                        filtered_values.append(v)
                        filtered_results.append(r)
                else:
                    filtered_values.append(v)
                    filtered_results.append(r)

            return filtered_values, filtered_results

        except Exception:
            return values, results

    def _average(self, values: List[Any]) -> Any:
        """Calculate average"""
        numeric = [v for v in values if isinstance(v, (int, float))]
        if numeric:
            return sum(numeric) / len(numeric)
        return values[0]

    def _weighted_average(
        self,
        values: List[Any],
        weights: Optional[Dict[str, float]],
        source_names: List[str]
    ) -> Any:
        """Calculate weighted average"""
        numeric = [v for v in values if isinstance(v, (int, float))]
        if not numeric:
            return values[0]

        if weights:
            total_weight = 0.0
            weighted_sum = 0.0
            for v, name in zip(values, source_names):
                if isinstance(v, (int, float)):
                    w = weights.get(name, 1.0)
                    weighted_sum += v * w
                    total_weight += w
            if total_weight > 0:
                return weighted_sum / total_weight

        return sum(numeric) / len(numeric)

    def _median(self, values: List[Any]) -> Any:
        """Calculate median"""
        numeric = sorted([v for v in values if isinstance(v, (int, float))])
        if not numeric:
            return values[0]
        n = len(numeric)
        if n % 2 == 0:
            return (numeric[n // 2 - 1] + numeric[n // 2]) / 2
        return numeric[n // 2]

    def _vote(self, values: List[Any]) -> Any:
        """Vote for most common value"""
        from collections import Counter
        counter = Counter(str(v) for v in values)
        return counter.most_common(1)[0][0]

    def _most_recent(
        self,
        values: List[Any],
        timestamps: List[float]
    ) -> tuple:
        """Get most recent value"""
        max_idx = timestamps.index(max(timestamps))
        return values[max_idx], 0.8

    def _most_reliable(
        self,
        results: List[DataSourceResult],
        weights: Optional[Dict[str, float]]
    ) -> tuple:
        """Get most reliable value based on latency and weights"""
        if not results:
            return None, 0.0

        best_result = results[0]
        best_score = 0.0

        for r in results:
            latency_score = max(0, 1.0 - (r.latency_ms / 10000))
            weight = weights.get(r.source_name, 1.0) if weights else 1.0
            score = latency_score * weight

            if score > best_score:
                best_score = score
                best_result = r

        return best_result.value, min(best_score * 0.8 + 0.2, 1.0)

    def _calculate_deviation(self, values: List[Any]) -> float:
        """Calculate standard deviation"""
        numeric = [v for v in values if isinstance(v, (int, float))]
        if len(numeric) < 2:
            return 0.0

        mean_val = sum(numeric) / len(numeric)
        variance = sum((v - mean_val) ** 2 for v in numeric) / len(numeric)
        return variance ** 0.5

    def _check_consistency(self, values: List[Any]) -> bool:
        """Check if values are consistent"""
        numeric = [v for v in values if isinstance(v, (int, float))]
        if len(numeric) < 2:
            return True

        mean_val = sum(numeric) / len(numeric)
        variance = sum((v - mean_val) ** 2 for v in numeric) / len(numeric)
        std_dev = variance ** 0.5

        if mean_val == 0:
            return std_dev == 0

        relative_deviation = std_dev / abs(mean_val)
        return relative_deviation <= self.config.consistency_threshold


@dataclass
class FusionOutput:
    """Output from data fusion"""
    success: bool
    fused_value: Any = None
    confidence: float = 0.0
    sources_used: List[str] = field(default_factory=list)
    method: str = ""
    deviation: float = 0.0
    is_consistent: bool = True
    values_count: int = 0
    error: Optional[str] = None
