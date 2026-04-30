# -*- coding: utf-8 -*-
"""Unit tests for nastool-reporters"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_terminal_reporter_import():
    from nastool_reporters.terminal import TerminalReporter
    assert TerminalReporter is not None

def test_json_reporter_import():
    from nastool_reporters.json_reporter import JSONReporter
    assert JSONReporter is not None

def test_html_reporter_import():
    from nastool_reporters.html_reporter import HTMLReporter
    assert HTMLReporter is not None

def test_friendly_reporter_import():
    from nastool_reporters.friendly_reporter import FriendlyReporter
    assert FriendlyReporter is not None

def test_terminal_reporter_instantiate():
    from nastool_reporters.terminal import TerminalReporter
    r = TerminalReporter()
    assert r is not None

if __name__ == "__main__":
    tests = [test_terminal_reporter_import, test_json_reporter_import,
             test_html_reporter_import, test_friendly_reporter_import,
             test_terminal_reporter_instantiate]
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
