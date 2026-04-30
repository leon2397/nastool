"""
NASTool Confidence Scoring System

Provides comprehensive confidence scoring for detection results.

Usage:
    from nastool_core.utils.confidence_scorer import ConfidenceScorer

    scorer = ConfidenceScorer()
    confidence = scorer.calculate_confidence(results, check_id="cpu_temp")
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .data_source import DataSourceResult
from .consistency_validator import ConsistencyValidator


@dataclass
class ConfidenceScore:
    """Confidence score result"""
    score: float  # 0.0-1.0
    factors: Dict[str, float]
    details: Dict[str, Any]
    timestamp: float


@dataclass
class ConfidenceConfig:
    """Confidence scoring configuration"""
    source_weight: float = 0.3
    consistency_weight: float = 0.3
    historical_weight: float = 0.2
    device_weight: float = 0.1
    check_weight: float = 0.1
    min_confidence: float = 0.3
    max_confidence: float = 1.0


class ConfidenceScorer:
    """
    Confidence scoring system for NASTool detection results.

    Features:
    - Multi-factor confidence calculation
    - Source reliability assessment
    - Data consistency evaluation
    - Historical trend analysis
    - Device-specific adjustments
    - Check-specific weights
    """

    def __init__(self, config: Optional[ConfidenceConfig] = None):
        """
        Initialize ConfidenceScorer.

        Args:
            config: Confidence scoring configuration
        """
        self.config = config or ConfidenceConfig()
        self.consistency_validator = ConsistencyValidator()
        self._historical_data = {}

    def calculate_confidence(
        self,
        results: List[DataSourceResult],
        check_id: Optional[str] = None,
        device_type: Optional[str] = None
    ) -> ConfidenceScore:
        """
        Calculate confidence score for detection results.

        Args:
            results: List of data source results
            check_id: Check identifier
            device_type: Device type

        Returns:
            ConfidenceScore object
        """
        if not results:
            return ConfidenceScore(
                score=0.0,
                factors={},
                details={"error": "No results provided"},
                timestamp=datetime.now().timestamp()
            )

        # Calculate individual factors
        source_score = self._calculate_source_score(results)
        consistency_score = self._calculate_consistency_score(results)
        historical_score = self._calculate_historical_score(results, check_id)
        device_score = self._calculate_device_score(device_type)
        check_score = self._calculate_check_score(check_id)

        # Weighted average
        total_weight = (
            self.config.source_weight +
            self.config.consistency_weight +
            self.config.historical_weight +
            self.config.device_weight +
            self.config.check_weight
        )

        weighted_score = (
            source_score * self.config.source_weight +
            consistency_score * self.config.consistency_weight +
            historical_score * self.config.historical_weight +
            device_score * self.config.device_weight +
            check_score * self.config.check_weight
        ) / total_weight

        # Apply bounds
        final_score = max(self.config.min_confidence, min(self.config.max_confidence, weighted_score))

        factors = {
            "source": source_score,
            "consistency": consistency_score,
            "historical": historical_score,
            "device": device_score,
            "check": check_score
        }

        details = {
            "source_count": len(results),
            "sources": [r.source for r in results],
            "check_id": check_id,
            "device_type": device_type,
            "timestamp": datetime.now().isoformat()
        }

        # Store historical data
        if check_id:
            self._store_historical_data(check_id, final_score)

        return ConfidenceScore(
            score=round(final_score, 3),
            factors=factors,
            details=details,
            timestamp=datetime.now().timestamp()
        )

    def _calculate_source_score(self, results: List[DataSourceResult]) -> float:
        """Calculate source reliability score"""
        if not results:
            return 0.0

        # Base score on number of sources
        source_count_score = min(len(results) / 5.0, 1.0)  # Max 1.0 for 5+ sources

        # Source quality assessment
        source_quality = sum(r.confidence for r in results) / len(results)

        # Combine scores
        return (source_count_score * 0.6) + (source_quality * 0.4)

    def _calculate_consistency_score(self, results: List[DataSourceResult]) -> float:
        """Calculate data consistency score"""
        if len(results) < 2:
            return 0.7  # Default score for insufficient data

        checks = self.consistency_validator.validate(results)
        overall_check = checks.get("overall")

        if overall_check:
            return overall_check.confidence
        return 0.7

    def _calculate_historical_score(self, results: List[DataSourceResult], check_id: Optional[str]) -> float:
        """Calculate historical consistency score"""
        if not check_id or check_id not in self._historical_data:
            return 0.8  # Default score for no historical data

        historical_scores = self._historical_data[check_id]
        if len(historical_scores) < 3:
            return 0.8

        # Calculate recent trend
        recent_scores = historical_scores[-5:]  # Last 5 scores
        avg_score = sum(recent_scores) / len(recent_scores)
        score_std = self._calculate_std(recent_scores)

        # Higher consistency (lower std) gives higher score
        consistency_factor = max(0, 1 - (score_std / 0.2))  # 0.2 is max expected std
        return (avg_score * 0.7) + (consistency_factor * 0.3)

    def _calculate_device_score(self, device_type: Optional[str]) -> float:
        """Calculate device-specific score"""
        # Device reliability scores based on known characteristics
        device_reliability = {
            "rk3588": 0.9,
            "rk3568": 0.85,
            "jetson": 0.95,
            "nas": 0.8,
            "generic": 0.7
        }

        return device_reliability.get(device_type, 0.7)

    def _calculate_check_score(self, check_id: Optional[str]) -> float:
        """Calculate check-specific score"""
        # Check reliability scores based on check type
        check_reliability = {
            "cpu_temp": 0.95,
            "gpu_temp": 0.9,
            "hdd_temp": 0.85,
            "network_speed": 0.8,
            "storage_usage": 0.9,
            "memory_usage": 0.95
        }

        return check_reliability.get(check_id, 0.8)

    def _store_historical_data(self, check_id: str, score: float):
        """Store historical confidence scores"""
        if check_id not in self._historical_data:
            self._historical_data[check_id] = []

        self._historical_data[check_id].append(score)
        # Keep only last 20 scores
        if len(self._historical_data[check_id]) > 20:
            self._historical_data[check_id] = self._historical_data[check_id][-20:]

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return variance ** 0.5

    def get_confidence_breakdown(self, results: List[DataSourceResult], check_id: Optional[str] = None, device_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed confidence breakdown.

        Args:
            results: List of data source results
            check_id: Check identifier
            device_type: Device type

        Returns:
            Detailed confidence breakdown
        """
        score = self.calculate_confidence(results, check_id, device_type)

        breakdown = {
            "confidence_score": score.score,
            "timestamp": datetime.now().isoformat(),
            "factors": score.factors,
            "details": score.details,
            "recommendations": self._generate_recommendations(score)
        }

        return breakdown

    def _generate_recommendations(self, score: ConfidenceScore) -> List[str]:
        """Generate recommendations based on confidence score"""
        recommendations = []

        if score.score < 0.5:
            recommendations.append("低置信度：建议增加更多数据源以提高准确性")
        elif score.score < 0.7:
            recommendations.append("中等置信度：考虑添加额外的验证步骤")

        # Check individual factors
        if score.factors.get("source", 0) < 0.6:
            recommendations.append("源可靠性低：建议检查数据源连接")
        if score.factors.get("consistency", 0) < 0.6:
            recommendations.append("数据一致性差：可能存在传感器问题")
        if score.factors.get("historical", 0) < 0.6:
            recommendations.append("历史一致性低：建议监控长期趋势")

        return recommendations


# Example usage
if __name__ == "__main__":
    from .data_source import DataFusionEngine, FusionMethod

    scorer = ConfidenceScorer()
    
    # Simulate temperature readings
    test_results = [
        DataSourceResult(value=50.2, source="thermal_zone", timestamp=datetime.now().timestamp(), confidence=0.9),
        DataSourceResult(value=51.0, source="sensors", timestamp=datetime.now().timestamp() + 1, confidence=0.85),
        DataSourceResult(value=50.8, source="hwmon", timestamp=datetime.now().timestamp() + 2, confidence=0.95),
        DataSourceResult(value=50.5, source="vcgencmd", timestamp=datetime.now().timestamp() + 3, confidence=0.9)
    ]
    
    breakdown = scorer.get_confidence_breakdown(test_results, check_id="cpu_temp", device_type="rk3588")
    print("Confidence Breakdown:")
    print(breakdown)
