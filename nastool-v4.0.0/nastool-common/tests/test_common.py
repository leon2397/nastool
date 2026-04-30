# -*- coding: utf-8 -*-
"""Unit tests for nastool-common"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_config_import():
    from nastool_common.config import Config
    assert Config is not None

def test_logger_import():
    from nastool_common.logger import get_logger
    logger = get_logger("test")
    assert logger is not None

def test_messages_import():
    from nastool_common.messages import msg
    assert msg is not None

def test_progress_import():
    from nastool_common.utils.progress import ProgressTracker, CheckStatus
    assert ProgressTracker is not None
    assert CheckStatus is not None

def test_registry_import():
    from nastool_common.utils.registry import Registry
    r = Registry("test")
    assert r is not None

def test_offline_storage_import():
    from nastool_common.utils.offline_storage import OfflineStorage
    assert OfflineStorage is not None

def test_logger_functional():
    from nastool_common.logger import get_logger
    import io, logging
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = get_logger("test_func")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("test")
    output = stream.getvalue()
    assert "test" in output

def test_config_init():
    from nastool_common.config import Config
    cfg = Config()
    assert cfg is not None

if __name__ == "__main__":
    tests = [
        test_config_import,
        test_logger_import,
        test_messages_import,
        test_progress_import,
        test_registry_import,
        test_offline_storage_import,
        test_logger_functional,
        test_config_init,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed")
