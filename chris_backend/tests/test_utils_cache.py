"""
Tests for cache utility.

Tests in-memory caching, TTL expiration, and invalidation.
"""
import pytest
import time


class TestCacheEntry:
    """Tests for CacheEntry class."""
    
    def test_cache_entry_not_expired(self):
        """Test that cache entry is not expired within TTL."""
        from src.utils.cache import CacheEntry
        
        entry = CacheEntry("test_value", ttl_seconds=60)
        
        assert entry.is_expired() is False
        assert entry.value == "test_value"
    
    def test_cache_entry_expired_after_ttl(self):
        """Test that cache entry expires after TTL."""
        from src.utils.cache import CacheEntry
        
        entry = CacheEntry("test_value", ttl_seconds=1)
        
        # Wait for expiration
        time.sleep(1.1)
        
        assert entry.is_expired() is True


class TestInMemoryCache:
    """Tests for InMemoryCache class."""
    
    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        from src.utils.cache import InMemoryCache
        
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl_seconds=60)
        
        result = cache.get("key1")
        assert result == "value1"
    
    def test_cache_get_nonexistent_key(self):
        """Test getting non-existent key returns None."""
        from src.utils.cache import InMemoryCache
        
        cache = InMemoryCache()
        result = cache.get("nonexistent")
        
        assert result is None
    
    def test_cache_get_expired_entry(self):
        """Test that expired entries return None."""
        from src.utils.cache import InMemoryCache
        
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl_seconds=1)
        
        # Wait for expiration
        time.sleep(1.1)
        
        result = cache.get("key1")
        assert result is None
    
    def test_cache_invalidate(self):
        """Test cache invalidation."""
        from src.utils.cache import InMemoryCache
        
        cache = InMemoryCache()
        cache.set("key1", "value1")
        
        cache.invalidate("key1")
        
        result = cache.get("key1")
        assert result is None
    
    def test_cache_invalidate_pattern(self):
        """Test pattern-based cache invalidation."""
        from src.utils.cache import InMemoryCache
        
        cache = InMemoryCache()
        cache.set("user:123:profile", "profile1")
        cache.set("user:123:settings", "settings1")
        cache.set("user:456:profile", "profile2")
        
        cache.invalidate_pattern("user:123")
        
        assert cache.get("user:123:profile") is None
        assert cache.get("user:123:settings") is None
        assert cache.get("user:456:profile") == "profile2"
    
    def test_cache_clear(self):
        """Test clearing all cache entries."""
        from src.utils.cache import InMemoryCache
        
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        from src.utils.cache import InMemoryCache
        
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        stats = cache.stats()
        
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2


class TestCacheUtilityFunctions:
    """Tests for cache utility functions."""
    
    def test_generate_cache_key(self):
        """Test cache key generation."""
        from src.utils.cache import generate_cache_key
        
        key1 = generate_cache_key("prefix", param1="value1", param2="value2")
        key2 = generate_cache_key("prefix", param1="value1", param2="value2")
        key3 = generate_cache_key("prefix", param1="value1", param2="different")
        
        # Same parameters should generate same key
        assert key1 == key2
        # Different parameters should generate different key
        assert key1 != key3
        # Key should start with prefix
        assert key1.startswith("prefix:")
    
    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test caching decorator for functions."""
        from src.utils.cache import cached, get_cache
        
        call_count = [0]
        
        @cached(ttl_seconds=60, key_prefix="test")
        async def expensive_function(param):
            call_count[0] += 1
            return f"result_{param}"
        
        # Clear cache first
        get_cache().clear()
        
        # First call should execute function
        result1 = await expensive_function("value1")
        assert result1 == "result_value1"
        assert call_count[0] == 1
        
        # Second call should use cache
        result2 = await expensive_function("value1")
        assert result2 == "result_value1"
        assert call_count[0] == 1  # Function not called again
    
    def test_invalidate_cache_function(self):
        """Test cache invalidation function."""
        from src.utils.cache import invalidate_cache, get_cache
        
        cache = get_cache()
        cache.set("pattern:key1", "value1")
        cache.set("pattern:key2", "value2")
        cache.set("other:key3", "value3")
        
        invalidate_cache("pattern")
        
        assert cache.get("pattern:key1") is None
        assert cache.get("pattern:key2") is None
        assert cache.get("other:key3") == "value3"
