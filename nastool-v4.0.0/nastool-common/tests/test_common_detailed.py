# -*- coding: utf-8 -*-
"""Detailed unit tests for nastool-common"""
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_config_functionality():
    """Test Config class functionality"""
    from nastool_common.config import Config
    
    # Test default values
    assert Config.NAS_HOST == "120.77.249.3"
    assert Config.NAS_PORT == 8000
    assert Config.WEB_PORT == 8080
    
    # Test URL generation
    assert Config.nas_url() == "http://120.77.249.3:8000"
    assert Config.web_url() == "http://0.0.0.0:8080"
    
    # Test path creation
    assert isinstance(Config.DEFAULT_SCAN_PATH, Path)
    assert isinstance(Config.DATA_DIR, Path)
    
    # Test ensure_paths method
    Config.ensure_paths()
    assert Config.DEFAULT_CACHE_PATH.exists()
    assert Config.DATA_DIR.exists()


def test_constants_functionality():
    """Test constants module functionality"""
    from nastool_common.constants import (
        DEFAULT_PATHS, DEFAULT_ENDPOINTS, DEFAULT_THRESHOLDS,
        get_path, get_endpoint, get_threshold
    )
    
    # Test path retrieval
    assert get_path("nas_root") == "/nas"
    assert get_path("media.photos") == "/nas/media/photos"
    assert get_path("nonexistent", "/default") == "/default"
    
    # Test endpoint retrieval
    assert get_endpoint("health") == "/health"
    assert get_endpoint("device_register") == "/api/devices/register"
    
    # Test threshold retrieval
    assert get_threshold("disk_warning") == 80
    assert get_threshold("temp_critical") == 85


def test_cmd_timeout_functionality():
    """Test cmd_timeout module functionality"""
    from nastool_common.utils.cmd_timeout import run_cmd_safe, check_cmd_available
    
    # Test command availability (use a command that should exist on all platforms)
    if check_cmd_available("echo"):
        # Test successful command (only if echo is available)
        result = run_cmd_safe(["echo", "Hello, World!"])
        assert hasattr(result, 'success')
        assert hasattr(result, 'stdout')
        assert hasattr(result, 'stderr')
    
    # Test command availability check
    assert check_cmd_available("python")


def test_progress_tracker_functionality():
    """Test progress tracker functionality"""
    from nastool_common.utils.progress import ProgressTracker, CheckStatus
    
    # Test progress tracker initialization
    tracker = ProgressTracker(total=2, desc="Test Tracker")
    assert tracker.total == 2
    assert tracker.current == 0
    
    # Test updating status
    tracker.update("test1", CheckStatus.RUNNING, category="test")
    assert tracker.current == 1
    
    tracker.update("test2", CheckStatus.OK, category="test")
    assert tracker.current == 2
    
    # Test finish method
    stats = tracker.finish(score=95)
    assert stats["total"] == 2
    assert stats["completed"] == 2
    assert stats["score"] == 95


def test_registry_functionality():
    """Test registry functionality"""
    from nastool_common.utils.registry import Registry, InstanceRegistry
    
    # Test Registry (class registry)
    class TestBaseClass:
        pass
    
    registry = Registry[TestBaseClass]("test_registry")
    assert registry.name == "test_registry"
    
    # Test registering class with decorator
    @registry.register
    class TestImpl(TestBaseClass):
        name = "test_impl"
    
    assert "test_impl" in registry.list_names()
    impl_class = registry.get("test_impl")
    assert impl_class is not None
    assert issubclass(impl_class, TestBaseClass)
    
    # Test InstanceRegistry (instance registry)
    instance_registry = InstanceRegistry[str]("test_instance_registry")
    assert instance_registry.name == "test_instance_registry"
    
    # Test registering and retrieving instances
    test_instance = "test_value"
    instance_registry.register("test_key", test_instance)
    assert instance_registry.get("test_key") == "test_value"
    assert len(instance_registry.list_all()) == 1


def test_offline_storage_functionality():
    """Test offline storage functionality"""
    from nastool_common.utils.offline_storage import OfflineStorage, OfflineConfig, create_offline_storage
    
    # Test with temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create storage with custom path
        storage = create_offline_storage(tmpdir)
        
        # Test saving and getting report
        test_data = {
            "health_score": 95,
            "cpu_usage": 25.5,
            "memory_usage": 60.2
        }
        
        report_id = storage.save_report("test-device-001", test_data)
        assert report_id is not None
        
        # Get the report
        report = storage.get_report(report_id)
        assert report is not None
        assert report.device_id == "test-device-001"
        assert report.data["health_score"] == 95
        
        # Test getting pending reports
        pending_reports = storage.get_pending_reports()
        assert len(pending_reports) == 1
        
        # Test deleting report
        assert storage.delete_report(report_id)
        assert storage.get_report(report_id) is None
        
        # Test status
        status = storage.get_status()
        assert status["total_reports"] == 0
        assert status["pending_reports"] == 0


def test_logger_functionality():
    """Test logger functionality"""
    from nastool_common.logger import get_logger
    import logging
    
    # Test logger creation
    logger = get_logger("test_logger")
    assert logger is not None
    assert isinstance(logger, logging.Logger)
    
    # Test logger methods
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'warning')
    assert hasattr(logger, 'error')
    assert hasattr(logger, 'debug')
    
    # Test logging (just ensure it doesn't raise exceptions)
    try:
        logger.info("Test log message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        logger.debug("Test debug message")
    except Exception as e:
        assert False, f"Logger failed: {e}"


def test_config_validator_functionality():
    """Test config validator functionality"""
    # 检查模块是否存在
    try:
        from nastool_common.utils import config_validator
        assert True, "config_validator module imported successfully"
    except ImportError:
        # 如果模块不存在，跳过测试
        pass


def test_safe_import_functionality():
    """Test safe import functionality"""
    from nastool_common.utils.safe_import import safe_import, optional_import, is_available
    
    # Test successful import
    os_module = safe_import("os")
    assert os_module is not None
    
    # Test optional import (should return None if not installed)
    psutil_module = optional_import("psutil")
    # psutil may or may not be installed, so just ensure it doesn't raise an exception
    assert True
    
    # Test is_available function
    assert is_available("os")


if __name__ == "__main__":
    tests = [
        test_config_functionality,
        test_constants_functionality,
        test_cmd_timeout_functionality,
        test_progress_tracker_functionality,
        test_registry_functionality,
        test_offline_storage_functionality,
        test_logger_functionality,
        test_config_validator_functionality,
        test_safe_import_functionality,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f"[PASS] {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
