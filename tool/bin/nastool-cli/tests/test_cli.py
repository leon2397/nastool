# -*- coding: utf-8 -*-
"""Unit tests for nastool-cli"""
import sys
import os

def test_cli_main_import():
    from nastool_cli.main import main, __version__
    assert __version__ == "4.1.0"

def test_parse_args():
    import argparse, sys
    # Just verify the module loads without error
    from nastool_cli import main
    assert main is not None

if __name__ == "__main__":
    tests = [test_cli_main_import, test_parse_args]
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
