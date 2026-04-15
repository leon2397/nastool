"""
Tests for constants module.
"""

import pytest
from constants import (
    DEFAULT_PATHS,
    DEFAULT_ENDPOINTS,
    DEFAULT_THRESHOLDS,
    get_path,
    get_endpoint,
    get_threshold,
    __version__,
)


class TestVersion:
    """Tests for version constant."""

    def test_version_format(self):
        """Test version follows semver format."""
        parts = __version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestDefaultPaths:
    """Tests for DEFAULT_PATHS."""

    def test_nas_root_exists(self):
        """Test NAS root path is defined."""
        assert "nas_root" in DEFAULT_PATHS
        assert DEFAULT_PATHS["nas_root"] == "/nas"

    def test_media_paths_exist(self):
        """Test media subdirectories are defined."""
        assert "media" in DEFAULT_PATHS
        media = DEFAULT_PATHS["media"]
        assert "photos" in media
        assert "videos" in media
        assert "music" in media
        assert "documents" in media

    def test_check_paths_list(self):
        """Test check_paths is a list."""
        assert "check_paths" in DEFAULT_PATHS
        assert isinstance(DEFAULT_PATHS["check_paths"], list)
        assert len(DEFAULT_PATHS["check_paths"]) > 0


class TestDefaultEndpoints:
    """Tests for DEFAULT_ENDPOINTS."""

    def test_health_endpoint(self):
        """Test health endpoint is defined."""
        assert "health" in DEFAULT_ENDPOINTS
        assert DEFAULT_ENDPOINTS["health"] == "/health"

    def test_device_endpoints(self):
        """Test device management endpoints."""
        assert "device_register" in DEFAULT_ENDPOINTS
        assert "device_heartbeat" in DEFAULT_ENDPOINTS
        assert DEFAULT_ENDPOINTS["device_register"] == "/api/devices/register"

    def test_media_endpoints(self):
        """Test media management endpoints."""
        assert "media" in DEFAULT_ENDPOINTS
        assert "media_scan" in DEFAULT_ENDPOINTS
        assert DEFAULT_ENDPOINTS["media_scan"] == "/api/media/scan"


class TestDefaultThresholds:
    """Tests for DEFAULT_THRESHOLDS."""

    def test_disk_thresholds(self):
        """Test disk space thresholds."""
        assert "disk_warning" in DEFAULT_THRESHOLDS
        assert "disk_critical" in DEFAULT_THRESHOLDS
        assert DEFAULT_THRESHOLDS["disk_warning"] < DEFAULT_THRESHOLDS["disk_critical"]

    def test_temperature_thresholds(self):
        """Test temperature thresholds."""
        assert "temp_warning" in DEFAULT_THRESHOLDS
        assert "temp_critical" in DEFAULT_THRESHOLDS
        assert DEFAULT_THRESHOLDS["temp_warning"] < DEFAULT_THRESHOLDS["temp_critical"]

    def test_write_speed_thresholds(self):
        """Test write speed thresholds."""
        assert "write_speed_warning" in DEFAULT_THRESHOLDS
        assert "write_speed_critical" in DEFAULT_THRESHOLDS
        assert (
            DEFAULT_THRESHOLDS["write_speed_warning"] > DEFAULT_THRESHOLDS["write_speed_critical"]
        )


class TestGetPath:
    """Tests for get_path function."""

    def test_top_level_path(self):
        """Test getting top-level path."""
        assert get_path("nas_root") == "/nas"
        assert get_path("temp") == "/tmp/nastool"

    def test_nested_path(self):
        """Test getting nested path with dot notation."""
        assert get_path("media.photos") == "/nas/media/photos"
        assert get_path("media.videos") == "/nas/media/videos"

    def test_nonexistent_path(self):
        """Test getting nonexistent path returns default."""
        assert get_path("nonexistent") == ""
        assert get_path("nonexistent", "/default") == "/default"

    def test_nonexistent_nested_path(self):
        """Test getting nonexistent nested path returns default."""
        assert get_path("media.nonexistent") == ""
        assert get_path("nonexistent.path", "/default") == "/default"


class TestGetEndpoint:
    """Tests for get_endpoint function."""

    def test_valid_endpoint(self):
        """Test getting valid endpoint."""
        assert get_endpoint("health") == "/health"
        assert get_endpoint("device_register") == "/api/devices/register"

    def test_invalid_endpoint(self):
        """Test getting invalid endpoint raises KeyError."""
        with pytest.raises(KeyError) as exc_info:
            get_endpoint("nonexistent")
        assert "nonexistent" in str(exc_info.value)


class TestGetThreshold:
    """Tests for get_threshold function."""

    def test_valid_threshold(self):
        """Test getting valid threshold."""
        assert get_threshold("disk_warning") == 80
        assert get_threshold("temp_critical") == 85

    def test_invalid_threshold(self):
        """Test getting invalid threshold raises KeyError."""
        with pytest.raises(KeyError) as exc_info:
            get_threshold("nonexistent")
        assert "nonexistent" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
