# -*- coding: utf-8 -*-
"""Unit tests for nastool-fixes"""
import sys
sys.path.insert(0, r"C:\tools416\nastool-fixes")

def test_fix_import():
    from nastool_fixes import Fix, FixResult
    assert Fix is not None
    assert FixResult is not None

def test_list_fixes():
    from nastool_fixes import list_available_fixes
    fixes = list_available_fixes()
    assert isinstance(fixes, dict)

def test_base_fix():
    from nastool_fixes.base import Fix, FixResult
    assert Fix is not None
    assert FixResult is not None

if __name__ == "__main__":
    tests = [test_fix_import, test_list_fixes, test_base_fix]
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
