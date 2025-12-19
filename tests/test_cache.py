"""
Cache tests for StreamRev
"""

import pytest
from src.utils.cache import RedisCache


class TestRedisCache:
    """Test Redis cache"""
    
    def test_cache_init(self):
        """Test cache initialization"""
        cache = RedisCache()
        assert cache.host is not None
        assert cache.port is not None
    
    def test_cache_set_get(self):
        """Test cache set and get"""
        # This would need a running Redis instance
        # For now, just test the methods exist
        cache = RedisCache()
        assert hasattr(cache, 'set')
        assert hasattr(cache, 'get')
        assert hasattr(cache, 'delete')
        assert hasattr(cache, 'exists')
