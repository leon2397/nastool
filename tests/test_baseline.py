#!/usr/bin/env python3
"""
Test script for baseline management functionality
"""

import sys
import os
import inspect

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

print(f"Python path: {sys.path}")

# Import and debug
from nastool_cli import compare
print(f"Imported module: {compare}")
print(f"Module path: {compare.__file__}")

from nastool_cli.compare import CompareAnalyzer
print(f"CompareAnalyzer class: {CompareAnalyzer}")
print(f"CompareAnalyzer methods: {[method for method in dir(CompareAnalyzer) if not method.startswith('_')]}")

def test_baseline_management():
    """Test baseline management functionality"""
    print("\nTesting baseline management...")
    
    analyzer = CompareAnalyzer()
    print(f"Analyzer instance: {analyzer}")
    print(f"Analyzer methods: {[method for method in dir(analyzer) if not method.startswith('_')]}")
    
    # Test 1: List all baselines
    print("\n1. Listing all baselines:")
    if hasattr(analyzer, 'list_baselines'):
        baselines = analyzer.list_baselines()
        print(f"Baselines: {baselines}")
    else:
        print("ERROR: list_baselines method not found!")
    
    # Test 2: Save a custom baseline
    print("\n2. Saving custom baseline:")
    if hasattr(analyzer, 'save_baseline'):
        custom_baseline = {
            "cpu_governor": "performance",
            "thermal_zone_0": 40,
            "memory_usage": 80
        }
        success = analyzer.save_baseline("test_device", custom_baseline)
        print(f"Save baseline success: {success}")
    else:
        print("ERROR: save_baseline method not found!")
    
    # Test 3: List baselines again to verify save
    print("\n3. Listing baselines after save:")
    if hasattr(analyzer, 'list_baselines'):
        baselines = analyzer.list_baselines()
        print(f"Baselines: {baselines}")
    else:
        print("ERROR: list_baselines method not found!")
    
    # Test 4: Test get_ideal_baseline
    print("\n4. Getting ideal baseline for test_device:")
    if hasattr(analyzer, '_get_ideal_baseline'):
        test_baseline = analyzer._get_ideal_baseline("test_device")
        print(f"Test device baseline: {test_baseline}")
    else:
        print("ERROR: _get_ideal_baseline method not found!")
    
    # Test 5: Test validation
    print("\n5. Testing baseline validation:")
    if hasattr(analyzer, 'validate_baseline'):
        valid_baseline = {"key": "value", "number": 123}
        invalid_baseline = {"key": []}  # Invalid value type
        print(f"Valid baseline: {analyzer.validate_baseline(valid_baseline)}")
        print(f"Invalid baseline: {analyzer.validate_baseline(invalid_baseline)}")
    else:
        print("ERROR: validate_baseline method not found!")
    
    # Test 6: Delete baseline
    print("\n6. Deleting test_device baseline:")
    if hasattr(analyzer, 'delete_baseline'):
        delete_success = analyzer.delete_baseline("test_device")
        print(f"Delete success: {delete_success}")
    else:
        print("ERROR: delete_baseline method not found!")
    
    # Test 7: List baselines to verify delete
    print("\n7. Listing baselines after delete:")
    if hasattr(analyzer, 'list_baselines'):
        baselines = analyzer.list_baselines()
        print(f"Baselines: {baselines}")
    else:
        print("ERROR: list_baselines method not found!")
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    test_baseline_management()
