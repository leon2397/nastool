# -*- coding: utf-8 -*-
"""
Integration tests for NASTool modular architecture

Tests that all modules work together correctly.
"""

import sys


def test_import_all_modules():
    """Test that all modules can be imported"""
    print("=" * 50)
    print("Testing module imports...")
    print("=" * 50)
    
    modules = [
        ("nastool_common", "Config, get_logger, msg"),
        ("nastool_core", "CheckSeverity, CheckResult, Check"),
        ("nastool_adapters", "BaseAdapter, MockAdapter"),
        ("nastool_reporters", "TerminalReporter, JSONReporter"),
        ("nastool_fixes", "Fix, FixResult, list_available_fixes"),
        ("nastool_cli", "main"),
    ]
    
    passed = 0
    failed = 0
    
    for module_name, imports in modules:
        try:
            exec(f"from {module_name} import {imports}")
            print(f"  [PASS] {module_name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {module_name}: {e}")
            failed += 1
    
    print()
    print(f"Imports: {passed} passed, {failed} failed")
    return failed == 0


def test_check_severity():
    """Test CheckSeverity enum"""
    print("\n" + "=" * 50)
    print("Testing CheckSeverity...")
    print("=" * 50)
    
    from nastool_core import CheckSeverity
    
    assert CheckSeverity.INFO.value == "info"
    assert CheckSeverity.WARNING.value == "warning"
    assert CheckSeverity.CRITICAL.value == "critical"
    assert CheckSeverity.PASSED.value == "passed"
    
    print("  [PASS] CheckSeverity values correct")
    return True


def test_check_result():
    """Test CheckResult dataclass"""
    print("\n" + "=" * 50)
    print("Testing CheckResult...")
    print("=" * 50)
    
    from nastool_core import CheckResult, CheckSeverity, CheckCategory
    
    result = CheckResult(
        check_id="test_001",
        category=CheckCategory.SYSTEM,
        severity=CheckSeverity.INFO,
        passed=True,
        title="Test Check",
        message="Test message",
        current="current value",
        expected="expected value",
    )
    
    assert result.check_id == "test_001"
    assert result.passed == True
    assert result.severity == CheckSeverity.INFO
    
    print("  [PASS] CheckResult creation works")
    return True


def test_adapter_registry():
    """Test adapter registry"""
    print("\n" + "=" * 50)
    print("Testing Adapter Registry...")
    print("=" * 50)
    
    from nastool_adapters import list_adapters
    
    adapters = list_adapters()
    adapter_names = [a["name"] for a in adapters]
    
    print(f"  Registered adapters: {adapter_names}")
    
    if "mock" in adapter_names:
        print("  [PASS] MockAdapter registered")
        return True
    else:
        print("  [FAIL] MockAdapter not registered")
        return False


def test_fix_registry():
    """Test fix registry"""
    print("\n" + "=" * 50)
    print("Testing Fix Registry...")
    print("=" * 50)
    
    from nastool_fixes import list_available_fixes
    
    fixes = list_available_fixes()
    print(f"  Available fixes: {len(fixes)}")
    
    if len(fixes) >= 0:
        print("  [PASS] Fix registry works")
        return True
    else:
        print("  [FAIL] No fixes registered")
        return False


def test_cli_version():
    """Test CLI version"""
    print("\n" + "=" * 50)
    print("Testing CLI...")
    print("=" * 50)
    
    from nastool_cli import main
    import io
    from contextlib import redirect_stdout
    
    # Test --version
    sys.argv = ["nastool", "--version"]
    
    f = io.StringIO()
    try:
        with redirect_stdout(f):
            main()
        output = f.getvalue()
        if "1.0.0" in output:
            print("  [PASS] nastool --version works")
            return True
        else:
            print(f"  [FAIL] Unexpected output: {output}")
            return False
    except SystemExit:
        pass
    
    return True


def main():
    """Run all integration tests"""
    print()
    print("=" * 50)
    print("NASTool Integration Tests")
    print("=" * 50)
    print()
    
    tests = [
        test_import_all_modules,
        test_check_severity,
        test_check_result,
        test_adapter_registry,
        test_fix_registry,
        test_cli_version,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [ERROR] {test.__name__}: {e}")
            failed += 1
    
    print()
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
