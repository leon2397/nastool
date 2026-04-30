"""
NASTool Data Validation Test Framework

Provides testing utilities for data fusion and consistency validation.

Usage:
    from nastool_core.utils.data_validation_test import DataValidationTester

    tester = DataValidationTester()
    results = tester.run_all_tests()
"""

import unittest
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .data_source import DataFusionEngine, DataSourceResult, FusionMethod, OutlierMethod
from .consistency_validator import ConsistencyValidator
from .confidence_scorer import ConfidenceScorer


@dataclass
class TestResult:
    """Test result"""
    test_name: str
    passed: bool
    message: str
    duration: float
    timestamp: float


class DataValidationTester:
    """
    Data validation test framework for NASTool.

    Features:
    - Unit tests for data fusion methods
    - Consistency validation tests
    - Confidence scoring tests
    - Edge case testing
    - Performance testing
    """

    def __init__(self):
        """Initialize DataValidationTester"""
        self.fusion_engine = DataFusionEngine()
        self.consistency_validator = ConsistencyValidator()
        self.confidence_scorer = ConfidenceScorer()
        self.test_results = []

    def run_all_tests(self) -> List[TestResult]:
        """
        Run all data validation tests.

        Returns:
            List of test results
        """
        test_functions = [
            self.test_fusion_methods,
            self.test_outlier_detection,
            self.test_consistency_validation,
            self.test_confidence_scoring,
            self.test_edge_cases,
            self.test_performance
        ]

        results = []
        for test_func in test_functions:
            result = test_func()
            results.extend(result)

        self.test_results = results
        return results

    def test_fusion_methods(self) -> List[TestResult]:
        """Test data fusion methods"""
        results = []

        # Test data
        test_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=52.0, source="s2", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=51.0, source="s3", timestamp=datetime.now().timestamp())
        ]

        # Test weighted average
        fused_value, metadata = self.fusion_engine.fuse_data(
            test_data, FusionMethod.WEIGHTED_AVERAGE
        )
        passed = 50.0 <= fused_value <= 52.0
        results.append(TestResult(
            test_name="Weighted Average Fusion",
            passed=passed,
            message=f"Fused value: {fused_value}",
            duration=0.0,
            timestamp=datetime.now().timestamp()
        ))

        # Test median
        fused_value, metadata = self.fusion_engine.fuse_data(
            test_data, FusionMethod.MEDIAN
        )
        passed = fused_value == 51.0
        results.append(TestResult(
            test_name="Median Fusion",
            passed=passed,
            message=f"Fused value: {fused_value}",
            duration=0.0,
            timestamp=datetime.now().timestamp()
        ))

        # Test mean
        fused_value, metadata = self.fusion_engine.fuse_data(
            test_data, FusionMethod.MEAN
        )
        passed = abs(fused_value - 51.0) < 0.1
        results.append(TestResult(
            test_name="Mean Fusion",
            passed=passed,
            message=f"Fused value: {fused_value}",
            duration=0.0,
            timestamp=datetime.now().timestamp()
        ))

        return results

    def test_outlier_detection(self) -> List[TestResult]:
        """Test outlier detection"""
        results = []

        # Test data with outlier
        test_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=52.0, source="s2", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=51.0, source="s3", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=80.0, source="s4", timestamp=datetime.now().timestamp())  # Outlier
        ]

        # Test IQR outlier detection
        fused_value, metadata = self.fusion_engine.fuse_data(test_data)
        passed = 50.0 <= fused_value <= 52.0  # Should exclude outlier
        results.append(TestResult(
            test_name="IQR Outlier Detection",
            passed=passed,
            message=f"Fused value: {fused_value}, sources: {metadata.get('sources', [])}",
            duration=0.0,
            timestamp=datetime.now().timestamp()
        ))

        return results

    def test_consistency_validation(self) -> List[TestResult]:
        """Test consistency validation"""
        results = []

        # Test time consistency
        test_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=51.0, source="s2", timestamp=datetime.now().timestamp() + 5),
            DataSourceResult(value=52.0, source="s3", timestamp=datetime.now().timestamp() + 10)
        ]

        consistency_checks = self.consistency_validator.validate(test_data)
        time_consistent = consistency_checks["time"].is_consistent
        results.append(TestResult(
            test_name="Time Consistency Check",
            passed=time_consistent,
            message=f"Time consistency: {time_consistent}",
            duration=0.0,
            timestamp=datetime.now().timestamp()
        ))

        # Test value consistency
        value_consistent = consistency_checks["value"].is_consistent
        results.append(TestResult(
            test_name="Value Consistency Check",
            passed=value_consistent,
            message=f"Value consistency: {value_consistent}",
            duration=0.0,
            timestamp=datetime.now().timestamp()
        ))

        return results

    def test_confidence_scoring(self) -> List[TestResult]:
        """Test confidence scoring"""
        results = []

        # Test confidence scoring
        test_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp(), confidence=0.9),
            DataSourceResult(value=51.0, source="s2", timestamp=datetime.now().timestamp(), confidence=0.85),
            DataSourceResult(value=52.0, source="s3", timestamp=datetime.now().timestamp(), confidence=0.95)
        ]

        score = self.confidence_scorer.calculate_confidence(
            test_data, check_id="cpu_temp", device_type="rk3588"
        )
        passed = 0.7 <= score.score <= 1.0
        results.append(TestResult(
            test_name="Confidence Scoring",
            passed=passed,
            message=f"Confidence score: {score.score}",
            duration=0.0,
            timestamp=datetime.now().timestamp()
        ))

        return results

    def test_edge_cases(self) -> List[TestResult]:
        """Test edge cases"""
        results = []

        # Test empty results
        fused_value, metadata = self.fusion_engine.fuse_data([])
        passed = fused_value is None
        results.append(TestResult(
            test_name="Empty Results",
            passed=passed,
            message=f"Empty results handled: {fused_value is None}",
            duration=0.0,
            timestamp=datetime.now().timestamp()
        ))

        # Test single result
        single_result = [DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp())]
        fused_value, metadata = self.fusion_engine.fuse_data(single_result)
        passed = fused_value == 50.0
        results.append(TestResult(
            test_name="Single Result",
            passed=passed,
            message=f"Single result handled: {fused_value}",
            duration=0.0,
            timestamp=datetime.now().timestamp()
        ))

        # Test time inconsistency
        inconsistent_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=51.0, source="s2", timestamp=datetime.now().timestamp() + 100)  # 100s difference
        ]
        fused_value, metadata = self.fusion_engine.fuse_data(inconsistent_data)
        passed = fused_value is None
        results.append(TestResult(
            test_name="Time Inconsistency",
            passed=passed,
            message=f"Time inconsistency handled: {fused_value is None}",
            duration=0.0,
            timestamp=datetime.now().timestamp()
        ))

        return results

    def test_performance(self) -> List[TestResult]:
        """Test performance"""
        results = []

        import time

        # Test fusion performance
        test_data = [
            DataSourceResult(value=50.0 + i, source=f"s{i}", timestamp=datetime.now().timestamp())
            for i in range(10)
        ]

        start_time = time.time()
        for _ in range(100):
            self.fusion_engine.fuse_data(test_data)
        duration = time.time() - start_time

        passed = duration < 1.0  # Should be fast
        results.append(TestResult(
            test_name="Fusion Performance",
            passed=passed,
            message=f"100 fusions took {duration:.3f}s",
            duration=duration,
            timestamp=datetime.now().timestamp()
        ))

        return results

    def generate_test_report(self) -> Dict[str, Any]:
        """
        Generate test report.

        Returns:
            Test report as dictionary
        """
        if not self.test_results:
            self.run_all_tests()

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failure_tests = total_tests - passed_tests

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failure_tests": failure_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "details": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration": r.duration
                }
                for r in self.test_results
            ]
        }

        return report


# Unit test class
class TestDataValidation(unittest.TestCase):
    """Unit tests for data validation components"""

    def setUp(self):
        """Set up test fixtures"""
        self.tester = DataValidationTester()

    def test_fusion_engine(self):
        """Test DataFusionEngine"""
        test_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=52.0, source="s2", timestamp=datetime.now().timestamp())
        ]

        fused_value, metadata = self.tester.fusion_engine.fuse_data(test_data)
        self.assertIsNotNone(fused_value)
        self.assertIn("s1", metadata.get("sources", []))
        self.assertIn("s2", metadata.get("sources", []))

    def test_consistency_validator(self):
        """Test ConsistencyValidator"""
        test_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=51.0, source="s2", timestamp=datetime.now().timestamp())
        ]

        checks = self.tester.consistency_validator.validate(test_data)
        self.assertTrue(checks["overall"].is_consistent)

    def test_confidence_scorer(self):
        """Test ConfidenceScorer"""
        test_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp(), confidence=0.9)
        ]

        score = self.tester.confidence_scorer.calculate_confidence(test_data)
        self.assertBetween(score.score, 0.0, 1.0)

    def assertBetween(self, value, min_val, max_val):
        """Assert value is between min and max"""
        self.assertTrue(min_val <= value <= max_val, f"{value} not between {min_val} and {max_val}")


if __name__ == "__main__":
    # Run tests
    tester = DataValidationTester()
    results = tester.run_all_tests()
    report = tester.generate_test_report()
    
    print("Data Validation Test Report:")
    print(f"Total Tests: {report['total_tests']}")
    print(f"Passed: {report['passed_tests']}")
    print(f"Failed: {report['failure_tests']}")
    print(f"Success Rate: {report['success_rate']:.1f}%")
    print("\nDetails:")
    for detail in report['details']:
        status = "✓" if detail['passed'] else "✗"
        print(f"{status} {detail['test_name']}: {detail['message']}")
