# -*- coding: utf-8 -*-
"""Test connection pool for nastool-adapters"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_pool_config():
    """Test PoolConfig class"""
    from nastool_adapters.utils.pool import PoolConfig, DEFAULT_POOL_CONFIG, SMALL_POOL_CONFIG, LARGE_POOL_CONFIG

    config = PoolConfig(pool_size=10, max_pool_size=20, timeout=30.0, max_retries=3, pool_block=False, enable_pool=True)

    assert config.pool_size == 10
    assert config.max_pool_size == 20
    assert config.timeout == 30.0
    assert config.max_retries == 3
    assert config.pool_block is False
    assert config.enable_pool is True

    assert DEFAULT_POOL_CONFIG.pool_size == 10
    assert DEFAULT_POOL_CONFIG.enable_pool is True

    assert SMALL_POOL_CONFIG.pool_size == 5
    assert SMALL_POOL_CONFIG.timeout == 10.0

    assert LARGE_POOL_CONFIG.pool_size == 20
    assert LARGE_POOL_CONFIG.max_pool_size == 50


def test_connection_pool_manager_init():
    """Test ConnectionPoolManager initialization"""
    from nastool_adapters.utils.pool import ConnectionPoolManager

    pool = ConnectionPoolManager(pool_size=5, max_pool_size=10, timeout=15.0, max_retries=2)

    assert pool.pool_size == 5
    assert pool.max_pool_size == 10
    assert pool.timeout == 15.0
    assert pool.max_retries == 2

    pool.close()


def test_connection_pool_request_methods():
    """Test ConnectionPoolManager HTTP methods"""
    from nastool_adapters.utils.pool import ConnectionPoolManager
    from unittest.mock import MagicMock, patch

    pool = ConnectionPoolManager(pool_size=5, max_pool_size=10, timeout=15.0, max_retries=2)

    mock_response = MagicMock()
    mock_response.data.decode.return_value = '{"status": "ok"}'

    with patch.object(pool._pool_manager, 'request', return_value=mock_response) as mock_request:
        result = pool.get("http://example.com/api")
        assert result is not None
        mock_request.assert_called_once()

    with patch.object(pool._pool_manager, 'request', return_value=mock_response) as mock_request:
        result = pool.post("http://example.com/api", body=b'{"data": "test"}')
        assert result is not None
        mock_request.assert_called_once()

    with patch.object(pool._pool_manager, 'request', return_value=mock_response) as mock_request:
        result = pool.put("http://example.com/api", body=b'{"data": "test"}')
        assert result is not None
        mock_request.assert_called_once()

    with patch.object(pool._pool_manager, 'request', return_value=mock_response) as mock_request:
        result = pool.delete("http://example.com/api")
        assert result is not None
        mock_request.assert_called_once()

    pool.close()


def test_connection_pool_clear():
    """Test ConnectionPoolManager clear method"""
    from nastool_adapters.utils.pool import ConnectionPoolManager

    pool = ConnectionPoolManager(pool_size=5, max_pool_size=10)
    pool.clear()

    assert pool._pool_manager is not None

    pool.close()


def test_connection_pool_context_manager():
    """Test ConnectionPoolManager as context manager"""
    from nastool_adapters.utils.pool import ConnectionPoolManager

    with ConnectionPoolManager(pool_size=5, max_pool_size=10) as pool:
        assert pool._pool_manager is not None

    assert pool._pool_manager is None


def test_get_pool_manager():
    """Test get_pool_manager function"""
    from nastool_adapters.utils.pool import get_pool_manager, clear_pool_manager, DEFAULT_POOL_CONFIG

    clear_pool_manager()

    manager1 = get_pool_manager()
    manager2 = get_pool_manager()

    assert manager1 is manager2

    clear_pool_manager()


def test_set_pool_config():
    """Test set_pool_config function"""
    from nastool_adapters.utils.pool import set_pool_config, get_pool_manager, clear_pool_manager, PoolConfig

    clear_pool_manager()

    from nastool_adapters.utils.pool import SMALL_POOL_CONFIG
    config = SMALL_POOL_CONFIG
    set_pool_config(config)

    manager = get_pool_manager()
    assert manager.pool_size == config.pool_size

    clear_pool_manager()


if __name__ == "__main__":
    tests = [
        test_pool_config,
        test_connection_pool_manager_init,
        test_connection_pool_request_methods,
        test_connection_pool_clear,
        test_connection_pool_context_manager,
        test_get_pool_manager,
        test_set_pool_config,
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
