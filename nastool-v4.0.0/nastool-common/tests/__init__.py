# tests for nastool-common
"""
Tests for nastool-common package
"""

def test_import():
    """Test that the package can be imported"""
    from nastool_common import Config, get_logger, msg
    assert Config is not None
    assert get_logger is not None
    assert msg is not None

def test_version():
    """Test version is defined"""
    import nastool_common
    assert hasattr(nastool_common, "__version__")
