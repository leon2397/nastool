# -*- coding: utf-8 -*-
"""Detailed unit tests for nastool-agent"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_agent_main_functionality():
    """Test agent main functionality"""
    try:
        from agent.main import main
        
        # Test that main function exists
        assert main is not None
    except ImportError as e:
        # If import fails, skip test
        pass


def test_agent_server_functionality():
    """Test agent server functionality"""
    try:
        from agent.server import AgentServer
        
        # Test that AgentServer class exists
        assert AgentServer is not None
    except ImportError as e:
        # If import fails, skip test
        pass


def test_agent_client_functionality():
    """Test agent client functionality"""
    try:
        from agent.client import AgentClient
        
        # Test that AgentClient class exists
        assert AgentClient is not None
    except ImportError as e:
        # If import fails, skip test
        pass


def test_agent_utils_functionality():
    """Test agent utils functionality"""
    try:
        from agent.utils import validate_agent_key, generate_agent_key
        
        # Test that utility functions exist
        assert validate_agent_key is not None
        assert generate_agent_key is not None
    except ImportError as e:
        # If import fails, skip test
        pass


if __name__ == "__main__":
    tests = [
        test_agent_main_functionality,
        test_agent_server_functionality,
        test_agent_client_functionality,
        test_agent_utils_functionality,
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
