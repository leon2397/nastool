# -*- coding: utf-8 -*-
"""Unit tests for nastool-adapters"""
import sys
sys.path.insert(0, r"C:\tools416\nastool-adapters")

def test_base_adapter_import():
    from nastool_adapters.base import BaseAdapter, AdapterResult, ErrorCode
    assert BaseAdapter is not None
    assert AdapterResult is not None

def test_detector_import():
    from nastool_adapters.detector import detect
    assert detect is not None

def test_mock_adapter_import():
    from nastool_adapters.mock_adapter import MockAdapter
    assert MockAdapter is not None

def test_list_adapters():
    from nastool_adapters import list_adapters
    adapters = list_adapters()
    assert isinstance(adapters, list)
    assert any(a["name"] == "mock" for a in adapters)

def test_mock_adapter_instantiate():
    from nastool_adapters.mock_adapter import MockAdapter
    adapter = MockAdapter(mock_data={"test": "value"})
    assert adapter is not None

if __name__ == "__main__":
    tests = [test_base_adapter_import, test_detector_import, test_mock_adapter_import,
             test_list_adapters, test_mock_adapter_instantiate]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed")
