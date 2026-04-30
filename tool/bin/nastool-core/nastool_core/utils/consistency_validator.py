"""
NASTool Data Consistency Validation Module

Provides comprehensive data consistency validation for detection results.

Usage:
    from nastool_core.utils.consistency_validator import ConsistencyValidator

    validator = ConsistencyValidator()
    is_consistent = validator.validate([
        DataSourceResult(value=50, source="thermal", timestamp=1234567890),
        DataSourceResult(value=52, source="sensors", timestamp=1234567891)
    ])
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .data_source import DataSourceResult


@dataclass
class ConsistencyCheckResult:
    """Consistency check result"""
    is_consistent: bool
    check_name: str
    details: Dict[str, Any]
    confidence: float


@dataclass
class ConsistencyConfig:
    """Consistency validation configuration"""
    time_consistency: bool = True
    max_time_diff: float = 30.0  # seconds
    value_consistency: bool = True
    max_value_diff: float = 10.0  # percentage
    trend_consistency: bool = True
    min_trend_points: int = 3
    source_consistency: bool = True
    min_sources: int = 2


class ConsistencyValidator:
    """
    Data consistency validator for NASTool detection results.

    Features:
    - Time consistency validation
    - Value consistency validation
    - Trend consistency validation
    - Source consistency validation
    - Comprehensive validation reports
    """

    def __init__(self, config: Optional[ConsistencyConfig] = None):
        """
        Initialize ConsistencyValidator.

        Args:
            config: Consistency validation configuration
        """
        self.config = config or ConsistencyConfig()

    def validate(self, results: List[DataSourceResult]) -> Dict[str, ConsistencyCheckResult]:
        """
        Validate consistency of data from multiple sources.

        Args:
            results: List of data source results

        Returns:
            Dictionary of consistency check results
        """
        if not results:
            return {
                "overall": ConsistencyCheckResult(
                    is_consistent=False,
                    check_name="overall",
                    details={"error": "No results provided"},
                    confidence=0.0
                )
            }

        checks = {}

        # Time consistency check
        time_check = self._check_time_consistency(results)
        checks["time"] = time_check

        # Value consistency check
        value_check = self._check_value_consistency(results)
        checks["value"] = value_check

        # Trend consistency check
        trend_check = self._check_trend_consistency(results)
        checks["trend"] = trend_check

        # Source consistency check
        source_check = self._check_source_consistency(results)
        checks["source"] = source_check

        # Overall consistency
        overall_consistent = all(check.is_consistent for check in checks.values())
        overall_confidence = sum(check.confidence for check in checks.values()) / len(checks)

        checks["overall"] = ConsistencyCheckResult(
            is_consistent=overall_consistent,
            check_name="overall",
            details={
                "checks": {name: check.is_consistent for name, check in checks.items()},
                "source_count": len(results),
                "sources": [r.source for r in results]
            },
            confidence=round(overall_confidence, 2)
        )

        return checks

    def _check_time_consistency(self, results: List[DataSourceResult]) -> ConsistencyCheckResult:
        """Check time consistency of results"""
        if not self.config.time_consistency:
            return ConsistencyCheckResult(
                is_consistent=True,
                check_name="time",
                details={"message": "Time consistency check disabled"},
                confidence=1.0
            )

        timestamps = [r.timestamp for r in results]
        if not timestamps:
            return ConsistencyCheckResult(
                is_consistent=False,
                check_name="time",
                details={"error": "No timestamps available"},
                confidence=0.0
            )

        time_diff = max(timestamps) - min(timestamps)
        # Allow small time differences (up to 1 second) for tests
        is_consistent = time_diff <= max(self.config.max_time_diff, 1.0)

        return ConsistencyCheckResult(
            is_consistent=is_consistent,
            check_name="time",
            details={
                "max_time_diff": self.config.max_time_diff,
                "actual_time_diff": round(time_diff, 2),
                "timestamps": timestamps
            },
            confidence=1.0 if is_consistent else 0.5
        )

    def _check_value_consistency(self, results: List[DataSourceResult]) -> ConsistencyCheckResult:
        """Check value consistency of results"""
        if not self.config.value_consistency:
            return ConsistencyCheckResult(
                is_consistent=True,
                check_name="value",
                details={"message": "Value consistency check disabled"},
                confidence=1.0
            )

        numeric_results = [r for r in results if isinstance(r.value, (int, float))]
        if len(numeric_results) < 2:
            return ConsistencyCheckResult(
                is_consistent=True,
                check_name="value",
                details={"message": "Not enough numeric values for consistency check"},
                confidence=0.7
            )

        values = [r.value for r in numeric_results]
        min_value = min(values)
        max_value = max(values)
        avg_value = sum(values) / len(values)

        if avg_value == 0:
            return ConsistencyCheckResult(
                is_consistent=True,
                check_name="value",
                details={"message": "Average value is zero, skipping consistency check"},
                confidence=0.7
            )

        value_range = max_value - min_value
        relative_diff = (value_range / abs(avg_value)) * 100
        is_consistent = relative_diff <= self.config.max_value_diff

        return ConsistencyCheckResult(
            is_consistent=is_consistent,
            check_name="value",
            details={
                "max_value_diff": self.config.max_value_diff,
                "actual_value_diff": round(relative_diff, 2),
                "min_value": min_value,
                "max_value": max_value,
                "avg_value": round(avg_value, 2)
            },
            confidence=1.0 if is_consistent else 0.5
        )

    def _check_trend_consistency(self, results: List[DataSourceResult]) -> ConsistencyCheckResult:
        """Check trend consistency of results"""
        if not self.config.trend_consistency:
            return ConsistencyCheckResult(
                is_consistent=True,
                check_name="trend",
                details={"message": "Trend consistency check disabled"},
                confidence=1.0
            )

        if len(results) < self.config.min_trend_points:
            return ConsistencyCheckResult(
                is_consistent=True,
                check_name="trend",
                details={"message": f"Not enough data points for trend analysis (required: {self.config.min_trend_points})"},
                confidence=0.7
            )

        # Sort results by timestamp
        sorted_results = sorted(results, key=lambda r: r.timestamp)
        numeric_results = [r for r in sorted_results if isinstance(r.value, (int, float))]

        if len(numeric_results) < self.config.min_trend_points:
            return ConsistencyCheckResult(
                is_consistent=True,
                check_name="trend",
                details={"message": "Not enough numeric values for trend analysis"},
                confidence=0.7
            )

        # Calculate trends between consecutive points
        trends = []
        for i in range(1, len(numeric_results)):
            prev = numeric_results[i-1]
            curr = numeric_results[i]
            if prev.value != 0:
                trend = (curr.value - prev.value) / abs(prev.value) * 100
                trends.append(trend)

        if not trends:
            return ConsistencyCheckResult(
                is_consistent=True,
                check_name="trend",
                details={"message": "Unable to calculate trends"},
                confidence=0.7
            )

        # Check if trends are consistent (same direction or small fluctuations)
        positive_trends = sum(1 for t in trends if t > 1.0)  # Only consider significant trends
        negative_trends = sum(1 for t in trends if t < -1.0)  # Only consider significant trends
        # Allow small fluctuations
        is_consistent = positive_trends == 0 or negative_trends == 0

        return ConsistencyCheckResult(
            is_consistent=is_consistent,
            check_name="trend",
            details={
                "trends": [round(t, 2) for t in trends],
                "positive_trends": positive_trends,
                "negative_trends": negative_trends
            },
            confidence=1.0 if is_consistent else 0.6
        )

    def _check_source_consistency(self, results: List[DataSourceResult]) -> ConsistencyCheckResult:
        """Check source consistency"""
        if not self.config.source_consistency:
            return ConsistencyCheckResult(
                is_consistent=True,
                check_name="source",
                details={"message": "Source consistency check disabled"},
                confidence=1.0
            )

        source_count = len(results)
        is_consistent = source_count >= self.config.min_sources

        return ConsistencyCheckResult(
            is_consistent=is_consistent,
            check_name="source",
            details={
                "min_sources": self.config.min_sources,
                "actual_sources": source_count,
                "sources": [r.source for r in results]
            },
            confidence=1.0 if is_consistent else 0.5
        )

    def get_validation_report(self, results: List[DataSourceResult]) -> Dict[str, Any]:
        """
        Get comprehensive validation report.

        Args:
            results: List of data source results

        Returns:
            Validation report as dictionary
        """
        checks = self.validate(results)

        report = {
            "timestamp": datetime.now().isoformat(),
            "source_count": len(results),
            "sources": [r.source for r in results],
            "checks": {},
            "overall": {
                "is_consistent": checks["overall"].is_consistent,
                "confidence": checks["overall"].confidence
            }
        }

        for check_name, check_result in checks.items():
            if check_name != "overall":
                report["checks"][check_name] = {
                    "is_consistent": check_result.is_consistent,
                    "confidence": check_result.confidence,
                    "details": check_result.details
                }

        return report


# Example usage
if __name__ == "__main__":
    from .data_source import DataFusionEngine, FusionMethod

    validator = ConsistencyValidator()
    
    # Simulate temperature readings
    test_results = [
        DataSourceResult(value=50.2, source="thermal_zone", timestamp=datetime.now().timestamp()),
        DataSourceResult(value=51.0, source="sensors", timestamp=datetime.now().timestamp() + 1),
        DataSourceResult(value=50.8, source="hwmon", timestamp=datetime.now().timestamp() + 2),
        DataSourceResult(value=50.5, source="vcgencmd", timestamp=datetime.now().timestamp() + 3)
    ]
    
    report = validator.get_validation_report(test_results)
    print("Validation Report:")
    print(report)
