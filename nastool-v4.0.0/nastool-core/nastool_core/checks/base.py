"""
checks/base.py - Base classes for all checks
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
import time


class CheckSeverity(Enum):
    """Check result severity levels"""

    INFO = "info"  # Informational, no action needed
    WARNING = "warning"  # Warning, should fix but not critical
    CRITICAL = "critical"  # Critical, must fix before proceeding
    PASSED = "passed"  # Check passed


class CheckCategory(Enum):
    """Check categories for organization"""

    SYSTEM = "system"
    NETWORK = "network"
    STORAGE = "storage"
    AI = "ai"
    SECURITY = "security"
    NAS = "nas"
    USB = "usb"  # v5.0.3


@dataclass
class DataSourceInfo:
    """Information about a data source used in detection"""
    name: str
    source_type: str
    available: bool = True
    priority: int = 100
    last_value: Any = None
    error: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class FusionResult:
    """Result from data fusion"""
    fused_value: Any
    confidence: float = 1.0
    sources_used: List[str] = field(default_factory=list)
    method: str = "average"
    deviation: float = 0.0
    is_consistent: bool = True


@dataclass
class CheckResult:
    """Result of a single check"""

    check_id: str  # Unique identifier: "python_version"
    category: CheckCategory  # Category for grouping
    severity: CheckSeverity  # Result severity
    passed: bool  # True if check passed
    title: str  # Human-readable title: "Python Version"
    current: str  # Current state: "3.6.9"
    expected: str  # Expected state: "3.8+"
    message: str  # Detailed message
    fix_available: bool = False  # Can be auto-fixed?
    fix_id: Optional[str] = None  # Corresponding fix ID
    fix_command: Optional[str] = None  # Command to fix
    fix_description: Optional[str] = None  # Human-readable fix description
    fix_risk: str = "low"  # Fix risk: low/medium/high
    url: Optional[str] = None  # Reference URL
    details: dict = field(default_factory=dict)  # Additional details
    data_sources: List[DataSourceInfo] = field(default_factory=list)
    fusion_result: Optional[FusionResult] = None
    confidence: float = 1.0


@dataclass
class CheckSummary:
    """Summary of all check results"""

    total: int = 0
    passed: int = 0
    warnings: int = 0
    critical: int = 0
    info: int = 0
    score: int = 0  # 0-100
    results: List[CheckResult] = field(default_factory=list)

    def add_result(self, result: CheckResult):
        """Add a result and update counters"""
        self.results.append(result)
        self.total += 1

        if result.passed:
            self.passed += 1
        elif result.severity == CheckSeverity.WARNING:
            self.warnings += 1
        elif result.severity == CheckSeverity.CRITICAL:
            self.critical += 1
        elif result.severity == CheckSeverity.INFO:
            self.info += 1

    def calculate_score(self):
        """Calculate overall health score (0-100) [legacy]"""
        if self.total == 0:
            return 0

        # Weighted scoring
        passed_weight = 100
        warning_weight = 70
        critical_weight = 0

        total_score = (
            self.passed * passed_weight
            + self.warnings * warning_weight
            + self.critical * critical_weight
        )
        max_score = self.total * passed_weight

        self.score = int((total_score / max_score) * 100) if max_score > 0 else 0
        return self.score

    def get_health_report(self, previous_score: int = None) -> "HealthReport":
        """
        Calculate detailed health score using HealthScorer (v4.0.2).
        Returns a HealthReport with category-level scores and recommendations.
        """
        from nastool_core.utils.health_scorer import calculate_health_score
        report = calculate_health_score(self.results, previous_score)
        self.score = report.overall_score
        return report


class Check(ABC):
    """Abstract base class for all checks"""

    # Subclasses should override these
    check_id: str = "base_check"
    category: CheckCategory = CheckCategory.SYSTEM
    title: str = "Base Check"
    description: str = "Base check class"

    @abstractmethod
    def run(self) -> CheckResult:
        """
        Run the check and return result.
        Must be implemented by subclasses.
        """
        pass

    def _run_command(self, cmd: str, timeout: int = 10) -> str:
        """Helper to run shell command"""
        import subprocess

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.stdout.strip()
        except Exception as e:
            return ""

    def _read_file(self, path: str) -> str:
        """Helper to read file contents"""
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception as e:
            return ""

    def _file_exists(self, path: str) -> bool:
        """Check if file exists"""
        import os

        return os.path.exists(path)

    def _command_exists(self, cmd: str) -> bool:
        """Check if command exists"""
        import shutil

        return shutil.which(cmd) is not None

    def _collect_from_sources(
        self,
        source_methods: Dict[str, Callable],
        fusion_method: str = "weighted_average"
    ) -> tuple:
        """
        Collect data from multiple sources and fuse results.

        Args:
            source_methods: Dict of {source_name: callable that returns data}
            fusion_method: Method to use for fusion ("average", "weighted_average", "max", "min", "vote")

        Returns:
            Tuple of (fused_value, FusionResult, list of DataSourceInfo)
        """
        from dataclasses import asdict
        import statistics

        sources_info = []
        valid_values = []
        source_weights = {}

        for name, method in source_methods.items():
            source_info = DataSourceInfo(
                name=name,
                source_type=name,
                timestamp=time.time()
            )

            try:
                value = method()
                if value is not None and value != "" and value != []:
                    source_info.available = True
                    source_info.last_value = value
                    valid_values.append(value)
                    source_weights[name] = 1.0
                else:
                    source_info.available = False
                    source_info.error = "No data returned"
            except Exception as e:
                source_info.available = False
                source_info.error = str(e)

            sources_info.append(source_info)

        if not valid_values:
            return None, None, sources_info

        if len(valid_values) == 1:
            fused_value = valid_values[0]
            confidence = 0.5
        else:
            try:
                if fusion_method == "average":
                    if all(isinstance(v, (int, float)) for v in valid_values):
                        fused_value = statistics.mean(valid_values)
                    else:
                        fused_value = valid_values[0]
                    confidence = 0.7

                elif fusion_method == "weighted_average":
                    if all(isinstance(v, (int, float)) for v in valid_values):
                        weights = [source_weights.get(s.name, 1.0) for s in sources_info if s.available]
                        total_weight = sum(weights)
                        if total_weight > 0:
                            fused_value = sum(v * w for v, w in zip(valid_values, weights)) / total_weight
                        else:
                            fused_value = statistics.mean(valid_values)
                    else:
                        fused_value = valid_values[0]
                    confidence = 0.8

                elif fusion_method == "max":
                    fused_value = max(valid_values)
                    confidence = 0.6

                elif fusion_method == "min":
                    fused_value = min(valid_values)
                    confidence = 0.6

                elif fusion_method == "vote":
                    from collections import Counter
                    counter = Counter(str(v) for v in valid_values)
                    fused_value = counter.most_common(1)[0][0]
                    confidence = 0.7 * (counter.most_common(1)[0][1] / len(valid_values))
                else:
                    fused_value = statistics.mean(valid_values) if all(isinstance(v, (int, float)) for v in valid_values) else valid_values[0]
                    confidence = 0.6

                if all(isinstance(v, (int, float)) for v in valid_values):
                    deviation = statistics.stdev(valid_values) if len(valid_values) > 1 else 0.0
                    mean_val = statistics.mean(valid_values)
                    if mean_val != 0:
                        relative_deviation = deviation / mean_val
                    else:
                        relative_deviation = 0.0
                else:
                    deviation = 0.0
                    relative_deviation = 0.0

            except Exception:
                fused_value = valid_values[0]
                confidence = 0.5
                deviation = 0.0
                relative_deviation = 0.0

        fusion_result = FusionResult(
            fused_value=fused_value,
            confidence=min(confidence, 1.0),
            sources_used=[s.name for s in sources_info if s.available],
            method=fusion_method,
            deviation=deviation,
            is_consistent=relative_deviation < 0.2
        )

        return fused_value, fusion_result, sources_info

    def run_with_cache(self, device_id: str, **kwargs) -> CheckResult:
        """
        Run check with caching.
        
        Args:
            device_id: Device identifier
            **kwargs: Additional parameters
            
        Returns:
            CheckResult
        """
        from nastool_core.utils.cache_manager import get_cache_manager
        
        cache = get_cache_manager()
        cached_result = cache.get(self.check_id, device_id, **kwargs)
        
        if cached_result:
            # Convert cached dict back to CheckResult
            from dataclasses import asdict
            result_dict = cached_result
            result_dict['category'] = CheckCategory(result_dict['category'])
            result_dict['severity'] = CheckSeverity(result_dict['severity'])
            return CheckResult(**result_dict)
        
        # Run check if not cached
        result = self.run()
        
        # Cache the result
        from dataclasses import asdict
        cache.set(self.check_id, device_id, asdict(result))
        
        return result
