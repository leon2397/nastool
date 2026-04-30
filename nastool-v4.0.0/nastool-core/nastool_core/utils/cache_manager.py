"""
Cache Manager for NASTool

Provides caching mechanism to reduce redundant checks and improve performance.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
from pathlib import Path


class CacheManager:
    """
    Cache manager for storing and retrieving check results.
    
    Features:
    - In-memory caching for fast access
    - Disk persistence for cross-session caching
    - TTL-based expiration
    - Hash-based key generation
    """
    
    def __init__(self, cache_dir: Optional[str] = None, default_ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            default_ttl: Default time-to-live in seconds
        """
        self.cache_dir = Path(cache_dir or Path.home() / ".nastool" / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self._load_from_disk()
    
    def _get_cache_file(self) -> Path:
        """Get cache file path"""
        return self.cache_dir / "check_cache.json"
    
    def _load_from_disk(self):
        """Load cache from disk"""
        try:
            cache_file = self._get_cache_file()
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Filter out expired items
                    now = datetime.now().timestamp()
                    self.memory_cache = {
                        key: value for key, value in data.items()
                        if value.get('expires_at', 0) > now
                    }
        except Exception:
            pass
    
    def _save_to_disk(self):
        """Save cache to disk"""
        try:
            cache_file = self._get_cache_file()
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory_cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def _generate_key(self, check_id: str, device_id: str, **kwargs) -> str:
        """
        Generate cache key based on check ID, device ID, and parameters.
        
        Args:
            check_id: Check identifier
            device_id: Device identifier
            **kwargs: Additional parameters
            
        Returns:
            Hashed cache key
        """
        data = f"{check_id}:{device_id}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def get(self, check_id: str, device_id: str, **kwargs) -> Optional[Any]:
        """
        Get cached result.
        
        Args:
            check_id: Check identifier
            device_id: Device identifier
            **kwargs: Additional parameters
            
        Returns:
            Cached result if valid, None otherwise
        """
        key = self._generate_key(check_id, device_id, **kwargs)
        item = self.memory_cache.get(key)
        
        if not item:
            return None
        
        # Check expiration
        now = datetime.now().timestamp()
        if item.get('expires_at', 0) < now:
            del self.memory_cache[key]
            self._save_to_disk()
            return None
        
        return item.get('value')
    
    def set(self, check_id: str, device_id: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set cached result.
        
        Args:
            check_id: Check identifier
            device_id: Device identifier
            value: Value to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        try:
            key = self._generate_key(check_id, device_id)
            ttl = ttl or self.default_ttl
            expires_at = datetime.now().timestamp() + ttl
            
            self.memory_cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'updated_at': datetime.now().timestamp()
            }
            
            self._save_to_disk()
            return True
        except Exception:
            return False
    
    def invalidate(self, check_id: Optional[str] = None, device_id: Optional[str] = None):
        """
        Invalidate cache entries.
        
        Args:
            check_id: Invalidate specific check
            device_id: Invalidate specific device
        """
        keys_to_delete = []
        
        for key, item in self.memory_cache.items():
            if check_id and check_id not in key:
                continue
            if device_id and device_id not in key:
                continue
            keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.memory_cache[key]
        
        self._save_to_disk()
    
    def clear(self):
        """Clear all cache"""
        self.memory_cache.clear()
        self._save_to_disk()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics
        """
        now = datetime.now().timestamp()
        valid = 0
        expired = 0
        
        for item in self.memory_cache.values():
            if item.get('expires_at', 0) > now:
                valid += 1
            else:
                expired += 1
        
        return {
            'total': len(self.memory_cache),
            'valid': valid,
            'expired': expired,
            'disk_size': self._get_cache_file().stat().st_size if self._get_cache_file().exists() else 0
        }


# Global cache instance
_cache_manager = None

def get_cache_manager() -> CacheManager:
    """
    Get global cache manager instance.
    
    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
