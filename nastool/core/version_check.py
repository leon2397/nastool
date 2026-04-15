"""
version_db/online.py - Fetch latest version info from online source
"""

import json
import os
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path


VERSION_URL = "https://raw.githubusercontent.com/leon2397/qizhiainas/main/arm/nastool/version_db/versions.json"
LOCAL_CACHE_FILE = "version_db/local.json"
CACHE_VALID_DAYS = 7


@dataclass
class VersionInfo:
    """Version information for a component"""

    latest: str
    min_recommended: str
    release_date: str
    release_notes: str
    url: str
    eol_versions: list = None
    compatibility: dict = None


@dataclass
class NewsItem:
    """Industry news item"""

    date: str
    vendor: str
    title: str
    summary: str
    impact: str
    url: str


class VersionDB:
    """Version database with online update support"""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.cache_file = self.base_path / LOCAL_CACHE_FILE
        self._data: Optional[Dict[str, Any]] = None

    def load(self, offline: bool = False) -> Dict[str, Any]:
        """
        Load version data.

        Args:
            offline: If True, skip online update

        Returns:
            Version data dictionary
        """
        # Try local cache first
        if self._load_cache():
            # Check if cache is still valid
            if self._is_cache_valid():
                return self._data

            # Cache expired, try online update
            if not offline:
                if self._fetch_online():
                    return self._data

        # No cache or online failed, use bundled fallback
        if self._load_bundled():
            return self._data

        return {}

    def _load_cache(self) -> bool:
        """Load from local cache file"""
        if not self.cache_file.exists():
            return False

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            return True
        except Exception as e:
            return False

    def _is_cache_valid(self) -> bool:
        """Check if cache is still within valid period"""
        if not self._data:
            return False

        updated_at = self._data.get("updated_at", "")
        if not updated_at:
            return False

        try:
            from datetime import datetime, timedelta

            cache_time = datetime.strptime(updated_at, "%Y-%m-%d")
            valid_until = cache_time + timedelta(days=CACHE_VALID_DAYS)
            return datetime.now() < valid_until
        except Exception as e:
            return False

    def _fetch_online(self) -> bool:
        """Fetch latest version data from online source"""
        try:
            import urllib.request

            req = urllib.request.Request(VERSION_URL, headers={"User-Agent": "nastool/1.0"})

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            # Update timestamp
            from datetime import datetime

            data["updated_at"] = datetime.now().strftime("%Y-%m-%d")

            # Save to cache
            self._data = data
            self._save_cache()
            return True

        except Exception as e:
            return False

    def _save_cache(self):
        """Save data to local cache"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            pass  # TODO: 添加日志

    def _load_bundled(self) -> bool:
        """Load bundled fallback data"""
        bundled_file = self.base_path / "version_db/versions.json"
        if not bundled_file.exists():
            return False

        try:
            with open(bundled_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            return True
        except Exception as e:
            return False

    def get_version(self, component: str) -> Optional[VersionInfo]:
        """Get version info for a specific component"""
        if not self._data:
            return None

        versions = self._data.get("versions", {})
        info = versions.get(component)

        if not info:
            return None

        return VersionInfo(
            latest=info.get("latest", ""),
            min_recommended=info.get("min_recommended", ""),
            release_date=info.get("release_date", ""),
            release_notes=info.get("release_notes", ""),
            url=info.get("url", ""),
            eol_versions=info.get("eol_versions", []),
            compatibility=info.get("compatibility", {}),
        )

    def get_news(self) -> list:
        """Get industry news items"""
        if not self._data:
            return []

        news_data = self._data.get("news", [])
        return [
            NewsItem(
                date=item.get("date", ""),
                vendor=item.get("vendor", ""),
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                impact=item.get("impact", ""),
                url=item.get("url", ""),
            )
            for item in news_data
        ]

    def force_update(self) -> bool:
        """Force update from online source"""
        return self._fetch_online()


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.

    Returns:
        -1 if v1 < v2
        0 if v1 == v2
        1 if v1 > v2
    """

    def normalize(v):
        # Extract numeric parts
        parts = []
        for part in v.replace("-", ".").split("."):
            # Handle versions like "560.35.03"
            try:
                parts.append(int("".join(c for c in part if c.isdigit())))
            except ValueError:
                parts.append(0)
        return parts

    p1 = normalize(v1)
    p2 = normalize(v2)

    # Pad to same length
    max_len = max(len(p1), len(p2))
    p1.extend([0] * (max_len - len(p1)))
    p2.extend([0] * (max_len - len(p2)))

    for a, b in zip(p1, p2):
        if a < b:
            return -1
        elif a > b:
            return 1

    return 0
