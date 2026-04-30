# -*- coding: utf-8 -*-
"""Test retry utilities for nastool-adapters"""
import sys
import os
import time

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_retry_decorator_success():
    """Test retry decorator with successful function"""
    from nastool_adapters.utils.retry import retry_on_network_error

    call_count = 0

    @retry_on_network_error(max_retries=3, delay=0.1)
    def successful_function():
        nonlocal call_count
        call_count += 1
        return "success"

    result = successful_function()
    assert result == "success"
    assert call_count == 1


def test_retry_decorator_failure():
    """Test retry decorator with failing function"""
    from nastool_adapters.utils.retry import retry_on_network_error, NetworkRetryError

    call_count = 0

    @retry_on_network_error(max_retries=3, delay=0.1)
    def failing_function():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Connection failed")

    try:
        failing_function()
        assert False, "Should have raised NetworkRetryError"
    except NetworkRetryError:
        pass

    assert call_count == 4  # 1 initial + 3 retries


def test_retry_decorator_eventual_success():
    """Test retry decorator with eventual success"""
    from nastool_adapters.utils.retry import retry_on_network_error

    call_count = 0

    @retry_on_network_error(max_retries=3, delay=0.1)
    def eventual_success():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Connection failed")
        return "success"

    result = eventual_success()
    assert result == "success"
    assert call_count == 3


def test_retry_config():
    """Test RetryConfig class"""
    from nastool_adapters.utils.retry import RetryConfig

    config = RetryConfig(max_retries=5, delay=2.0, backoff=2.0, max_delay=60.0)

    assert config.max_retries == 5
    assert config.delay == 2.0
    assert config.backoff == 2.0
    assert config.max_delay == 60.0
    assert config.enable is True

    assert config.get_delay(0) == 2.0
    assert config.get_delay(1) == 4.0
    assert config.get_delay(2) == 8.0
    assert config.get_delay(10) == 60.0  # Capped at max_delay


def test_default_retry_config():
    """Test default retry config"""
    from nastool_adapters.utils.retry import DEFAULT_RETRY_CONFIG, FAST_RETRY_CONFIG, SLOW_RETRY_CONFIG

    assert DEFAULT_RETRY_CONFIG.max_retries == 3
    assert DEFAULT_RETRY_CONFIG.delay == 1.0
    assert DEFAULT_RETRY_CONFIG.enable is True

    assert FAST_RETRY_CONFIG.max_retries == 2
    assert FAST_RETRY_CONFIG.delay == 0.5

    assert SLOW_RETRY_CONFIG.max_retries == 5
    assert SLOW_RETRY_CONFIG.delay == 2.0


def test_retry_with_result_check():
    """Test retry with result check"""
    from nastool_adapters.utils.retry import retry_with_result_check

    call_count = 0

    @retry_with_result_check(max_retries=3, delay=0.1, result_check=lambda x: x is not None)
    def unstable_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return None
        return "success"

    result = unstable_function()
    assert result == "success"
    assert call_count == 3


if __name__ == "__main__":
    tests = [
        test_retry_decorator_success,
        test_retry_decorator_failure,
        test_retry_decorator_eventual_success,
        test_retry_config,
        test_default_retry_config,
        test_retry_with_result_check,
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
