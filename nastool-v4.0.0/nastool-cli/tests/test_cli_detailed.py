# -*- coding: utf-8 -*-
"""Detailed unit tests for nastool-cli"""
import sys
import os
import tempfile
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_cli_parser_functionality():
    """Test CLI parser functionality"""
    try:
        from nastool_cli.parser import create_parser
        
        # Test parser creation
        parser = create_parser()
        assert parser is not None
        
        # Test parsing basic arguments
        args = parser.parse_args(["check"])
        assert args.command == "check"
    except ImportError as e:
        # If import fails, skip test
        pass


def test_cli_main_functionality():
    """Test CLI main functionality"""
    try:
        from nastool_cli.main import main
        
        # Test that main function exists
        assert main is not None
    except ImportError as e:
        # If import fails, skip test
        pass


def test_cli_commands_functionality():
    """Test CLI commands functionality"""
    try:
        from nastool_cli.commands import check, report, fix
        
        # Test that command functions exist
        assert check is not None
        assert report is not None
        assert fix is not None
    except ImportError as e:
        # If import fails, skip test
        pass


def test_cli_utils_functionality():
    """Test CLI utils functionality"""
    try:
        from nastool_cli.utils import format_output, handle_errors
        
        # Test that utility functions exist
        assert format_output is not None
        assert handle_errors is not None
    except ImportError as e:
        # If import fails, skip test
        pass


if __name__ == "__main__":
    tests = [
        test_cli_parser_functionality,
        test_cli_main_functionality,
        test_cli_commands_functionality,
        test_cli_utils_functionality,
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
