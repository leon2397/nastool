"""
conftest.py — pytest configuration + shared fixtures for nastool tests

Sets up Python path + shared mocks + test fixtures.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Python path setup ──────────────────────────────────────────────────────────
nastool_root = Path(__file__).parent.parent.resolve()
if str(nastool_root) not in sys.path:
    sys.path.insert(0, str(nastool_root))


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_device_env():
    """Simulate a generic ARM64 device environment."""
    env = {
        "ARCH": "aarch64",
        "MACHINE": "generic-arm64",
        "PLATFORM": "linux",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_device_jetson():
    """Simulate a Jetson Orin NX device environment."""
    env = {
        "ARCH": "aarch64",
        "MACHINE": "jetson-orin-nx",
        "PLATFORM": "linux",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_device_synology():
    """Simulate a Synology NAS device environment."""
    env = {
        "ARCH": "x86_64",
        "MACHINE": "synology-ds920plus",
        "PLATFORM": "linux",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_nas_backend():
    """Mock NAS backend HTTP responses."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "ok", "version": "1.0.0"}
    with patch("urllib.request.urlopen", return_value=mock_resp):
        yield mock_resp


@pytest.fixture
def sample_check_result_passed():
    """A passing CheckResult sample."""
    from checks.base import CheckResult, CheckSeverity, CheckCategory

    return CheckResult(
        check_id="python_version",
        category=CheckCategory.SYSTEM,
        severity=CheckSeverity.PASSED,
        passed=True,
        title="Python Version",
        current="3.10.12",
        expected="3.8+",
        message="Python version is up to date.",
        fix_available=False,
    )


@pytest.fixture
def sample_check_result_warning():
    """A WARNING CheckResult sample."""
    from checks.base import CheckResult, CheckSeverity, CheckCategory

    return CheckResult(
        check_id="memory_check",
        category=CheckCategory.SYSTEM,
        severity=CheckSeverity.WARNING,
        passed=False,
        title="Memory Check",
        current="85% used",
        expected="< 80%",
        message="Memory usage is high.",
        fix_available=True,
        fix_id="cleanup_tmp_space",
    )


@pytest.fixture
def sample_check_result_critical():
    """A CRITICAL CheckResult sample."""
    from checks.base import CheckResult, CheckSeverity, CheckCategory

    return CheckResult(
        check_id="smart_health",
        category=CheckCategory.STORAGE,
        severity=CheckSeverity.CRITICAL,
        passed=False,
        title="SMART Health",
        current="FAIL - Reallocated Sector Count",
        expected="PASS",
        message="Disk SMART indicates imminent failure.",
        fix_available=False,
    )


@pytest.fixture
def sample_check_summary():
    """A CheckSummary with mixed results for scoring tests."""
    from checks.base import CheckResult, CheckSeverity, CheckCategory, CheckSummary

    results = [
        CheckResult(
            check_id="python_version",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.PASSED,
            passed=True,
            title="Python Version",
            current="3.10.12",
            expected="3.8+",
            message="OK",
        ),
        CheckResult(
            check_id="memory_check",
            category=CheckCategory.SYSTEM,
            severity=CheckSeverity.WARNING,
            passed=False,
            title="Memory",
            current="85%",
            expected="< 80%",
            message="High memory usage",
        ),
        CheckResult(
            check_id="smart_health",
            category=CheckCategory.STORAGE,
            severity=CheckSeverity.CRITICAL,
            passed=False,
            title="SMART",
            current="FAIL",
            expected="PASS",
            message="Disk failing",
        ),
    ]
    return CheckSummary(
        total=3, passed=1, warnings=1, critical=1, results=results
    )


@pytest.fixture
def sample_device_profile():
    """A sample DeviceProfile with minimal required fields."""
    from profiles.loader import DeviceProfile

    data = {
        "jetson-xavier-nx": {
            "name": "NVIDIA Jetson Xavier NX",
            "vendor": "NVIDIA",
            "arch": "aarch64",
            "chip_type": "nvidia_jetson",
            "ai_type": "npu",
            "checks": {
                "python_version": {"min_version": "3.8"},
                "memory_check": {"threshold": 90},
            },
            "fixes": ["install_python", "install_cuda"],
        }
    }
    return DeviceProfile(data)


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config.yaml for testing."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "system:\n  python_min_version: '3.8'\n  python_recommended_version: '3.10'\n"
    )
    return config_path


# ── Markers ────────────────────────────────────────────────────────────────────
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (mocked environment)"
    )
    config.addinivalue_line(
        "markers", "functional: Functional tests (real execution)"
    )
    config.addinivalue_line("markers", "smoke: Smoke tests (core functionality)")
    config.addinivalue_line("markers", "slow: Slow tests (>5 seconds)")
