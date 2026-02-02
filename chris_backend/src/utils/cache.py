"""
Cache utility for CHRIS Backend API.

Implements in-memory TTL-based caching for read-heavy endpoints like
citywide risk and sponge zones. Supports cache invalidation on writes.

For production distributed systems, consider Redis or Memcached.
"""
import time
import logging
from typing import Any, Optional, Dict, Callable
from functools import wraps
from threading import Lock
import json
import hashlib

logger = logging.getLogger(__name__)


class CacheEntry:
    """
    Represents a single cache entry with value and expiration time.
    """
    
    def __init__(self, value: Any, ttl_seconds: int):
        """
        Initialize cache entry.
        
        Args:
            value: Cached value
            ttl_seconds: Time-to-live in seconds
        """
        self.value = value
        self.expires_at = time.time() + ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() > self.expires_at


class InMemoryCache:
    """
    Thread-safe in-memory cache with TTL support.
    
    Features:
    - TTL-based expiration
    - Cache invalidation by pattern
    - Automatic cleanup of expired entries
    - Thread-safe operations
    """
    
    def __init__(self):
        """Initialize cache with empty storage."""
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Clean up every 5 minutes
    
    def _cleanup_expired(self):
        """
        Remove expired entries to prevent memory leak.
        Called periodically during cache operations.
        """
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            self._last_cleanup = now
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        self._cleanup_expired()
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                logger.debug(f"Cache MISS: {key}")
                return None
            
            if entry.is_expired():
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: {key}")
                return None
            
            logger.debug(f"Cache HIT: {key}")
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """
        Set cache entry with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time-to-live in seconds (default: 5 minutes)
        """
        with self._lock:
            self._cache[key] = CacheEntry(value, ttl_seconds)
            logger.debug(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
    
    def invalidate(self, key: str):
        """
        Invalidate specific cache entry.
        
        Args:
            key: Cache key to invalidate
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.info(f"Cache INVALIDATED: {key}")
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all cache entries matching a pattern.
        
        Args:
            pattern: String pattern to match (simple substring match)
        """
        with self._lock:
            keys_to_delete = [
                key for key in self._cache.keys()
                if pattern in key
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
            
            if keys_to_delete:
                logger.info(f"Cache INVALIDATED pattern '{pattern}': {len(keys_to_delete)} entries")
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache CLEARED: {count} entries removed")
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(
                1 for entry in self._cache.values()
                if entry.is_expired()
            )
            
            return {
                "total_entries": total_entries,
                "active_entries": total_entries - expired_entries,
                "expired_entries": expired_entries
            }


# Global cache instance
_cache = InMemoryCache()


def get_cache() -> InMemoryCache:
    """
    Get global cache instance.
    
    Returns:
        InMemoryCache instance
    """
    return _cache


def generate_cache_key(prefix: str, **kwargs) -> str:
    """
    Generate cache key from prefix and parameters.
    
    Args:
        prefix: Cache key prefix (e.g., 'citywide_risk', 'sponge_zones')
        **kwargs: Parameters to include in cache key
        
    Returns:
        Generated cache key
    """
    # Sort kwargs for consistent key generation
    sorted_params = sorted(kwargs.items())
    params_str = json.dumps(sorted_params, sort_keys=True)
    
    # Hash parameters for shorter keys
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
    
    return f"{prefix}:{params_hash}"


# PUBLIC_INTERFACE
def cached(ttl_seconds: int = 300, key_prefix: str = "default"):
    """
    Decorator to cache function results with TTL.
    
    Usage:
    ```python
    @cached(ttl_seconds=600, key_prefix="citywide_risk")
    async def get_citywide_risk_data(start_year: int = None, end_year: int = None):
        # ... expensive operation
        return data
    ```
    
    Args:
        ttl_seconds: Time-to-live in seconds (default: 5 minutes)
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            cache_key = generate_cache_key(key_prefix, **kwargs)
            
            # Try to get from cache
            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                logger.info(f"Returning cached result for {func.__name__}")
                return cached_value
            
            # Cache miss - execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            _cache.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


# PUBLIC_INTERFACE
def invalidate_cache(pattern: str):
    """
    Invalidate cache entries matching pattern.
    
    Usage:
    ```python
    # Invalidate all citywide risk caches
    invalidate_cache("citywide_risk")
    
    # Invalidate all sponge zone caches
    invalidate_cache("sponge_zones")
    ```
    
    Args:
        pattern: Pattern to match for invalidation
    """
    _cache.invalidate_pattern(pattern)
    logger.info(f"Invalidated cache pattern: {pattern}")
