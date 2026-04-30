"""
Integration tests for data fusion and validation components
"""

import unittest
from datetime import datetime
from typing import List

from nastool_core.utils.data_source import DataFusionEngine, DataSourceResult, FusionMethod
from nastool_core.utils.consistency_validator import ConsistencyValidator
from nastool_core.utils.confidence_scorer import ConfidenceScorer
from nastool_core.checks.system.cpu_temp import CPUTempCheck


class TestDataFusionIntegration(unittest.TestCase):
    """Integration tests for data fusion components"""

    def setUp(self):
        """Set up test fixtures"""
        self.fusion_engine = DataFusionEngine()
        self.consistency_validator = ConsistencyValidator()
        self.confidence_scorer = ConfidenceScorer()
        self.cpu_temp_check = CPUTempCheck()

    def test_data_fusion_basic(self):
        """Test basic data fusion functionality"""
        # Create test data
        test_results = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=52.0, source="s2", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=51.0, source="s3", timestamp=datetime.now().timestamp())
        ]

        # Test weighted average fusion
        fused_value, metadata = self.fusion_engine.fuse_data(
            test_results, FusionMethod.WEIGHTED_AVERAGE
        )
        self.assertIsNotNone(fused_value)
        self.assertGreaterEqual(fused_value, 50.0)
        self.assertLessEqual(fused_value, 52.0)
        self.assertIn("sources", metadata)
        self.assertEqual(len(metadata["sources"]), 3)

        # Test median fusion
        fused_value, metadata = self.fusion_engine.fuse_data(
            test_results, FusionMethod.MEDIAN
        )
        self.assertIsNotNone(fused_value)
        self.assertEqual(fused_value, 51.0)

    def test_outlier_detection(self):
        """Test outlier detection in data fusion"""
        # Create test data with outlier
        test_results = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=52.0, source="s2", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=51.0, source="s3", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=80.0, source="s4", timestamp=datetime.now().timestamp())  # Outlier
        ]

        # Test fusion with outlier detection
        fused_value, metadata = self.fusion_engine.fuse_data(test_results)
        self.assertIsNotNone(fused_value)
        self.assertGreaterEqual(fused_value, 50.0)
        self.assertLessEqual(fused_value, 52.0)  # Should exclude outlier
        self.assertIn("sources", metadata)
        self.assertLess(len(metadata["sources"]), 4)  # Outlier should be excluded

    def test_consistency_validation(self):
        """Test consistency validation"""
        # Create consistent test data
        consistent_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=51.0, source="s2", timestamp=datetime.now().timestamp() + 5),
            DataSourceResult(value=52.0, source="s3", timestamp=datetime.now().timestamp() + 10)
        ]

        # Test consistency validation
        checks = self.consistency_validator.validate(consistent_data)
        self.assertTrue(checks["overall"].is_consistent)
        self.assertTrue(checks["time"].is_consistent)
        self.assertTrue(checks["value"].is_consistent)

        # Create inconsistent test data (time)
        inconsistent_time_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=51.0, source="s2", timestamp=datetime.now().timestamp() + 100)  # 100s difference
        ]

        checks = self.consistency_validator.validate(inconsistent_time_data)
        self.assertFalse(checks["time"].is_consistent)

    def test_confidence_scoring(self):
        """Test confidence scoring"""
        # Create test data
        test_results = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp(), confidence=0.9),
            DataSourceResult(value=51.0, source="s2", timestamp=datetime.now().timestamp(), confidence=0.85),
            DataSourceResult(value=52.0, source="s3", timestamp=datetime.now().timestamp(), confidence=0.95)
        ]

        # Test confidence scoring
        score = self.confidence_scorer.calculate_confidence(
            test_results, check_id="cpu_temp", device_type="rk3588"
        )
        self.assertGreaterEqual(score.score, 0.0)
        self.assertLessEqual(score.score, 1.0)
        self.assertGreater(score.score, 0.7)  # Should have high confidence

    def test_cpu_temp_integration(self):
        """Test CPU temperature check integration"""
        # Test that CPU temp check can be instantiated
        self.assertIsInstance(self.cpu_temp_check, CPUTempCheck)

        # Test that it has the required attributes
        self.assertEqual(self.cpu_temp_check.check_id, "cpu_temperature")
        self.assertEqual(self.cpu_temp_check.title, "CPU 温度检测")

    def test_end_to_end_fusion(self):
        """Test end-to-end data fusion pipeline"""
        # Create test data
        test_results = [
            DataSourceResult(value=50.0, source="thermal_zone", timestamp=datetime.now().timestamp(), confidence=0.9),
            DataSourceResult(value=51.0, source="sensors", timestamp=datetime.now().timestamp(), confidence=0.85),
            DataSourceResult(value=50.5, source="hwmon", timestamp=datetime.now().timestamp(), confidence=0.95)
        ]

        # Step 1: Consistency validation
        consistency_checks = self.consistency_validator.validate(test_results)
        # Print debug information
        print("Consistency checks:")
        for name, check in consistency_checks.items():
            print(f"{name}: {check.is_consistent} - {check.details}")
        self.assertTrue(consistency_checks["overall"].is_consistent)

        # Step 2: Data fusion
        fused_value, metadata = self.fusion_engine.fuse_data(test_results)
        self.assertIsNotNone(fused_value)
        self.assertGreaterEqual(fused_value, 50.0)
        self.assertLessEqual(fused_value, 51.0)

        # Step 3: Confidence scoring
        confidence = self.confidence_scorer.calculate_confidence(test_results, check_id="cpu_temp")
        self.assertGreater(confidence.score, 0.8)

    def test_edge_cases(self):
        """Test edge cases"""
        # Test empty results
        fused_value, metadata = self.fusion_engine.fuse_data([])
        self.assertIsNone(fused_value)
        self.assertIn("error", metadata)

        # Test single result
        single_result = [DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp())]
        fused_value, metadata = self.fusion_engine.fuse_data(single_result)
        self.assertIsNotNone(fused_value)
        self.assertEqual(fused_value, 50.0)

        # Test time inconsistency
        inconsistent_data = [
            DataSourceResult(value=50.0, source="s1", timestamp=datetime.now().timestamp()),
            DataSourceResult(value=51.0, source="s2", timestamp=datetime.now().timestamp() + 100)  # 100s difference
        ]
        fused_value, metadata = self.fusion_engine.fuse_data(inconsistent_data)
        self.assertIsNone(fused_value)
        self.assertIn("error", metadata)

    def test_performance(self):
        """Test performance of data fusion components"""
        import time

        # Create test data
        test_data = [
            DataSourceResult(value=50.0 + i, source=f"s{i}", timestamp=datetime.now().timestamp())
            for i in range(10)
        ]

        # Test fusion performance
        start_time = time.time()
        for _ in range(100):
            self.fusion_engine.fuse_data(test_data)
        fusion_duration = time.time() - start_time
        self.assertLess(fusion_duration, 1.0)  # Should be fast

        # Test consistency validation performance
        start_time = time.time()
        for _ in range(100):
            self.consistency_validator.validate(test_data)
        consistency_duration = time.time() - start_time
        self.assertLess(consistency_duration, 1.0)  # Should be fast

        # Test confidence scoring performance
        start_time = time.time()
        for _ in range(100):
            self.confidence_scorer.calculate_confidence(test_data)
        confidence_duration = time.time() - start_time
        self.assertLess(confidence_duration, 1.0)  # Should be fast


if __name__ == "__main__":
    unittest.main()
