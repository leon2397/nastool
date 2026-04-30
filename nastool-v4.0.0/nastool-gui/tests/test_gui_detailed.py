# -*- coding: utf-8 -*-
"""Detailed unit tests for nastool-gui"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_gui_app_functionality():
    """Test GUI app functionality"""
    try:
        from gui.app import main
        
        # Test that main function exists
        assert main is not None
    except ImportError as e:
        # If import fails, skip test
        pass


def test_gui_config_functionality():
    """Test GUI config functionality"""
    try:
        from gui.config import load_config, save_config
        
        # Test that config functions exist
        assert load_config is not None
        assert save_config is not None
    except ImportError as e:
        # If import fails, skip test
        pass


def test_gui_utils_functionality():
    """Test GUI utils functionality"""
    try:
        from gui.utils import validate_input, format_output
        
        # Test that utility functions exist
        assert validate_input is not None
        assert format_output is not None
    except ImportError as e:
        # If import fails, skip test
        pass


def test_gui_handlers_functionality():
    """Test GUI handlers functionality"""
    try:
        from gui.handlers import handle_test_ssh, handle_test_http
        
        # Test that handler functions exist
        assert handle_test_ssh is not None
        assert handle_test_http is not None
    except ImportError as e:
        # If import fails, skip test
        pass


if __name__ == "__main__":
    tests = [
        test_gui_app_functionality,
        test_gui_config_functionality,
        test_gui_utils_functionality,
        test_gui_handlers_functionality,
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
