"""
Unit tests for Phase 1 Core Framework Upgrade

Tests for:
- Enhanced Check base class with multi-source data support
- DataSource abstraction layer
- DataFusionEngine
- DeviceIdentifier
- ThresholdConfig
- DynamicThresholdAdjuster
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCheckBaseEnhancements(unittest.TestCase):
    """Test enhanced Check base class"""

    def test_data_source_info_creation(self):
        """Test DataSourceInfo dataclass"""
        from nastool_core.checks.base import DataSourceInfo

        info = DataSourceInfo(
            name="test_source",
            source_type="file",
            available=True,
            priority=100,
            last_value=42.0,
            timestamp=time.time()
        )

        self.assertEqual(info.name, "test_source")
        self.assertTrue(info.available)
        self.assertEqual(info.last_value, 42.0)

    def test_fusion_result_creation(self):
        """Test FusionResult dataclass"""
        from nastool_core.checks.base import FusionResult

        result = FusionResult(
            fused_value=50.0,
            confidence=0.85,
            sources_used=["source1", "source2"],
            method="weighted_average",
            deviation=2.5,
            is_consistent=True
        )

        self.assertEqual(result.fused_value, 50.0)
        self.assertGreater(result.confidence, 0.8)
        self.assertTrue(result.is_consistent)

    def test_collect_from_sources_single_source(self):
        """Test _collect_from_sources with single source"""
        from nastool_core.checks.base import Check

        class TestCheck(Check):
            check_id = "test_check"

            def run(self):
                pass

        check = TestCheck()
        sources = {"source1": lambda: 42.0}

        fused, fusion_result, sources_info = check._collect_from_sources(sources)

        self.assertEqual(fused, 42.0)
        self.assertEqual(len(sources_info), 1)
        self.assertTrue(sources_info[0].available)

    def test_collect_from_sources_multiple_sources(self):
        """Test _collect_from_sources with multiple sources"""
        from nastool_core.checks.base import Check

        class TestCheck(Check):
            check_id = "test_check"

            def run(self):
                pass

        check = TestCheck()
        sources = {
            "source1": lambda: 40.0,
            "source2": lambda: 50.0,
            "source3": lambda: 45.0,
        }

        fused, fusion_result, sources_info = check._collect_from_sources(sources, "average")

        self.assertIsNotNone(fused)
        self.assertEqual(len([s for s in sources_info if s.available]), 3)
        self.assertGreater(fusion_result.confidence, 0.5)

    def test_collect_from_sources_with_failure(self):
        """Test _collect_from_sources with some sources failing"""
        from nastool_core.checks.base import Check

        class TestCheck(Check):
            check_id = "test_check"

            def run(self):
                pass

        check = TestCheck()
        sources = {
            "source1": lambda: 40.0,
            "source2": lambda: (_ for _ in ()).throw(Exception("Test error")),
            "source3": lambda: 45.0,
        }

        fused, fusion_result, sources_info = check._collect_from_sources(sources)

        self.assertIsNotNone(fused)
        self.assertEqual(len([s for s in sources_info if s.available]), 2)
        self.assertEqual(len([s for s in sources_info if not s.available]), 1)


class TestDataSourceAbstraction(unittest.TestCase):
    """Test DataSource abstraction layer"""

    def test_file_data_source_availability(self):
        """Test FileDataSource availability check"""
        from nastool_core.utils.data_source import FileDataSource

        source = FileDataSource("test", "/nonexistent/path/file.txt")
        self.assertFalse(source.is_available())

    def test_command_data_source_availability(self):
        """Test CommandDataSource availability check"""
        from nastool_core.utils.data_source import CommandDataSource

        source = CommandDataSource("ls", "ls -la")
        self.assertTrue(source.is_available())

    def test_proc_data_source(self):
        """Test ProcDataSource"""
        from nastool_core.utils.data_source import ProcDataSource

        source = ProcDataSource("cpuinfo", "/proc/cpuinfo")

        if os.path.exists("/proc/cpuinfo"):
            self.assertTrue(source.is_available())
            result = source.read()
            self.assertTrue(result.success)
            self.assertIsNotNone(result.value)
        else:
            self.assertFalse(source.is_available())

    def test_data_source_registry(self):
        """Test DataSourceRegistry"""
        from nastool_core.utils.data_source import (
            DataSourceRegistry,
            DataSourceConfig,
            DataSourceType,
            DataSource
        )

        class TestDataSource(DataSource):
            def _check_availability(self):
                return True

            def _read(self):
                return "test_value"

        registry = DataSourceRegistry()
        config = DataSourceConfig(
            name="test",
            source_type=DataSourceType.COMMAND,
            priority=100
        )
        source = TestDataSource(config)

        registry.register(source)
        self.assertEqual(registry.get("test"), source)
        self.assertEqual(len(registry.get_all()), 1)

        registry.unregister("test")
        self.assertIsNone(registry.get("test"))


class TestDataFusionEngine(unittest.TestCase):
    """Test DataFusionEngine"""

    def test_fusion_average(self):
        """Test average fusion method"""
        from nastool_core.utils.data_source import (
            DataFusionEngine,
            FusionMethod,
            DataSourceResult
        )

        engine = DataFusionEngine()
        engine.config.method = FusionMethod.AVERAGE

        results = [
            DataSourceResult(success=True, value=40.0, source_name="s1"),
            DataSourceResult(success=True, value=50.0, source_name="s2"),
            DataSourceResult(success=True, value=45.0, source_name="s3"),
        ]

        output = engine.fuse(results)

        self.assertTrue(output.success)
        self.assertEqual(output.fused_value, 45.0)
        self.assertGreater(output.confidence, 0.5)

    def test_fusion_weighted_average(self):
        """Test weighted average fusion method"""
        from nastool_core.utils.data_source import (
            DataFusionEngine,
            FusionMethod,
            DataSourceResult
        )

        engine = DataFusionEngine()
        engine.config.method = FusionMethod.WEIGHTED_AVERAGE

        results = [
            DataSourceResult(success=True, value=40.0, source_name="s1"),
            DataSourceResult(success=True, value=50.0, source_name="s2"),
        ]

        weights = {"s1": 2.0, "s2": 1.0}
        output = engine.fuse(results, weights)

        self.assertTrue(output.success)
        self.assertEqual(output.fused_value, 43.33)
        self.assertGreater(output.confidence, 0.5)

    def test_fusion_with_outlier_removal(self):
        """Test fusion with outlier removal"""
        from nastool_core.utils.data_source import (
            DataFusionEngine,
            FusionMethod,
            DataSourceResult
        )

        engine = DataFusionEngine()
        engine.config.method = FusionMethod.AVERAGE
        engine.config.outlier_removal = True

        results = [
            DataSourceResult(success=True, value=40.0, source_name="s1"),
            DataSourceResult(success=True, value=50.0, source_name="s2"),
            DataSourceResult(success=True, value=100.0, source_name="s3"),
        ]

        output = engine.fuse(results)

        self.assertTrue(output.success)
        self.assertLess(output.fused_value, 60.0)

    def test_fusion_consistency_check(self):
        """Test consistency checking"""
        from nastool_core.utils.data_source import (
            DataFusionEngine,
            FusionMethod,
            DataSourceResult
        )

        engine = DataFusionEngine()
        engine.config.method = FusionMethod.AVERAGE
        engine.config.consistency_threshold = 0.2

        results = [
            DataSourceResult(success=True, value=45.0, source_name="s1"),
            DataSourceResult(success=True, value=46.0, source_name="s2"),
            DataSourceResult(success=True, value=44.0, source_name="s3"),
        ]

        output = engine.fuse(results)

        self.assertTrue(output.is_consistent)

    def test_fusion_insufficient_sources(self):
        """Test fusion with insufficient sources"""
        from nastool_core.utils.data_source import (
            DataFusionEngine,
            DataSourceResult
        )

        engine = DataFusionEngine()
        engine.config.min_sources = 2

        results = [
            DataSourceResult(success=True, value=40.0, source_name="s1"),
        ]

        output = engine.fuse(results)

        self.assertFalse(output.success)
        self.assertIn("Insufficient", output.error)


class TestDeviceIdentifier(unittest.TestCase):
    """Test DeviceIdentifier"""

    def test_device_type_enum(self):
        """Test DeviceType enum"""
        from nastool_core.utils.device_identifier import DeviceType

        self.assertEqual(DeviceType.RK3588.value, "rk3588")
        self.assertEqual(DeviceType.JETSON_XAVIER.value, "jetson_xavier")

    def test_device_category_enum(self):
        """Test DeviceCategory enum"""
        from nastool_core.utils.device_identifier import DeviceCategory

        self.assertEqual(DeviceCategory.NAS.value, "nas")
        self.assertEqual(DeviceCategory.AI_SERVER.value, "ai_server")

    def test_device_info_creation(self):
        """Test DeviceInfo dataclass"""
        from nastool_core.utils.device_identifier import (
            DeviceInfo,
            DeviceType,
            DeviceCategory
        )

        info = DeviceInfo(
            device_id="test_rk3588",
            device_type=DeviceType.RK3588,
            device_name="Rockchip RK3588",
            manufacturer="Rockchip",
            category=DeviceCategory.AI_SERVER,
            chip_model="RK3588"
        )

        self.assertEqual(info.device_type, DeviceType.RK3588)
        self.assertEqual(info.manufacturer, "Rockchip")

    @patch('platform.system')
    def test_identify_windows(self, mock_system):
        """Test device identification on Windows"""
        from nastool_core.utils.device_identifier import DeviceIdentifier, DeviceType

        mock_system.return_value = "Windows"

        identifier = DeviceIdentifier()
        device_info = identifier.identify()

        self.assertEqual(device_info.device_type, DeviceType.X86)

    def test_get_device_type(self):
        """Test get_device_type convenience method"""
        from nastool_core.utils.device_identifier import DeviceIdentifier

        identifier = DeviceIdentifier()
        device_type = identifier.get_device_type()

        self.assertIsNotNone(device_type)


class TestThresholdConfig(unittest.TestCase):
    """Test ThresholdConfig"""

    def test_threshold_value_creation(self):
        """Test ThresholdValue dataclass"""
        from nastool_core.utils.threshold_config import ThresholdValue, ThresholdLevel

        value = ThresholdValue(
            level=ThresholdLevel.WARNING,
            value=75.0,
            description="CPU temp warning"
        )

        self.assertEqual(value.level, ThresholdLevel.WARNING)
        self.assertEqual(value.value, 75.0)

    def test_threshold_config_creation(self):
        """Test ThresholdConfig dataclass"""
        from nastool_core.utils.threshold_config import ThresholdConfig

        config = ThresholdConfig(
            check_id="cpu_temperature",
            warning=75.0,
            critical=85.0,
            unit="°C"
        )

        self.assertEqual(config.check_id, "cpu_temperature")
        self.assertEqual(config.warning, 75.0)

    def test_get_threshold_default(self):
        """Test get_threshold with default device"""
        from nastool_core.utils.threshold_config import get_threshold

        threshold = get_threshold("cpu_temperature")

        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.check_id, "cpu_temperature")
        self.assertEqual(threshold.warning, 75.0)

    def test_get_threshold_device_specific(self):
        """Test get_threshold with device-specific config"""
        from nastool_core.utils.threshold_config import get_threshold

        threshold = get_threshold("cpu_temperature", device_type="rk3588")

        self.assertIsNotNone(threshold)
        self.assertEqual(threshold.warning, 70.0)

    def test_evaluate_value(self):
        """Test evaluate_value"""
        from nastool_core.utils.threshold_config import (
            evaluate_threshold,
            ThresholdLevel
        )

        result = evaluate_threshold("cpu_temperature", 80.0)
        self.assertEqual(result, ThresholdLevel.WARNING)

        result = evaluate_threshold("cpu_temperature", 90.0)
        self.assertEqual(result, ThresholdLevel.CRITICAL)

        result = evaluate_threshold("cpu_temperature", 45.0)
        self.assertEqual(result, ThresholdLevel.OPTIMAL)


class TestDynamicThresholdAdjuster(unittest.TestCase):
    """Test DynamicThresholdAdjuster"""

    def test_adjust_threshold_normal(self):
        """Test adjust_threshold with normal environment"""
        from nastool_core.utils.threshold_config import DynamicThresholdAdjuster

        adjuster = DynamicThresholdAdjuster()

        environment = {
            "load_avg": [0.5, 0.3, 0.1],
            "ambient_temp": 25.0,
            "uptime_hours": 24,
            "hour": 12
        }

        adjusted = adjuster.adjust_threshold(75.0, "cpu_temperature", environment)

        self.assertIsNotNone(adjusted)
        self.assertGreater(adjusted, 0)

    def test_adjust_threshold_high_load(self):
        """Test adjust_threshold with high load"""
        from nastool_core.utils.threshold_config import DynamicThresholdAdjuster

        adjuster = DynamicThresholdAdjuster()

        environment = {
            "load_avg": [3.0, 2.5, 2.0],
            "ambient_temp": 30.0,
            "uptime_hours": 200,
            "hour": 14
        }

        base_threshold = 75.0
        adjusted = adjuster.adjust_threshold(base_threshold, "cpu_temperature", environment)

        self.assertGreater(adjusted, base_threshold)

    def test_get_environment_score(self):
        """Test get_environment_score"""
        from nastool_core.utils.threshold_config import DynamicThresholdAdjuster

        adjuster = DynamicThresholdAdjuster()

        environment = {
            "load_avg": [0.5, 0.3, 0.1],
            "ambient_temp": 25.0,
            "uptime_hours": 24
        }

        score = adjuster.get_environment_score(environment)

        self.assertGreater(score, 80)
        self.assertLessEqual(score, 100)

    def test_get_environment_score_poor(self):
        """Test get_environment_score with poor conditions"""
        from nastool_core.utils.threshold_config import DynamicThresholdAdjuster

        adjuster = DynamicThresholdAdjuster()

        environment = {
            "load_avg": [3.5, 3.0, 2.5],
            "ambient_temp": 40.0,
            "uptime_hours": 800
        }

        score = adjuster.get_environment_score(environment)

        self.assertLess(score, 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
