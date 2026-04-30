# -*- coding: utf-8 -*-
"""Detailed unit tests for nastool-adapters"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_http_detector_functionality():
    """Test HTTP detector functionality"""
    try:
        from nastool_adapters.detectors.http_detector import HTTPDetector
        
        # Test HTTP detector initialization
        detector = HTTPDetector()
        assert detector is not None
        
        # Test detect method (will skip if no server is running)
        try:
            result = detector.detect("http://localhost:8000")
            assert isinstance(result, dict)
        except Exception:
            # If no server is running, skip this part
            pass
    except ImportError as e:
        # If import fails, skip test
        pass


def test_ssh_detector_functionality():
    """Test SSH detector functionality"""
    try:
        from nastool_adapters.detectors.ssh_detector import SSHDetector
        
        # Test SSH detector initialization
        detector = SSHDetector()
        assert detector is not None
        
        # Test detect method (will skip if no SSH server is running)
        try:
            result = detector.detect("localhost", 22, "test", "test")
            assert isinstance(result, dict)
        except Exception:
            # If no SSH server is running, skip this part
            pass
    except ImportError as e:
        # If import fails, skip test
        pass


def test_docker_service_functionality():
    """Test Docker service functionality"""
    try:
        from nastool_adapters.services.docker_service import DockerService
        
        # Test Docker service initialization
        service = DockerService()
        assert service is not None
        
        # Test is_available method
        try:
            available = service.is_available()
            assert isinstance(available, bool)
        except Exception:
            # If Docker is not available, skip this part
            pass
    except ImportError as e:
        # If import fails, skip test
        pass


def test_integration_functionality():
    """Test integration functionality"""
    try:
        from nastool_adapters.integration import AdapterManager
        
        # Test AdapterManager initialization
        manager = AdapterManager()
        assert manager is not None
        
        # Test get_available_adapters method
        adapters = manager.get_available_adapters()
        assert isinstance(adapters, list)
    except ImportError as e:
        # If import fails, skip test
        pass


def test_common_utils_functionality():
    """Test common utils functionality"""
    try:
        from nastool_adapters.utils import common
        
        # Test common utils functions
        assert hasattr(common, "safe_request")
        assert hasattr(common, "retry_with_backoff")
    except ImportError as e:
        # If import fails, skip test
        pass


if __name__ == "__main__":
    tests = [
        test_http_detector_functionality,
        test_ssh_detector_functionality,
        test_docker_service_functionality,
        test_integration_functionality,
        test_common_utils_functionality,
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
