"""
Redis/KeyDB caching layer
"""

import redis
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis/KeyDB cache handler"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 6379, 
                 db: int = 0, password: Optional[str] = None):
        """
        Initialize Redis connection
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.client = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection"""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}")
            self.client = None
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Cache get failed: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Convert to JSON if not string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            if ttl:
                return self.client.setex(key, ttl, value)
            else:
                return self.client.set(key, value)
        except Exception as e:
            logger.error(f"Cache set failed: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete failed: {str(e)}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if exists, False otherwise
        """
        if not self.client:
            return False
        
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists check failed: {str(e)}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all keys in current database
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            self.client.flushdb()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {str(e)}")
            return False
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment counter
        
        Args:
            key: Cache key
            amount: Amount to increment
            
        Returns:
            New value or None
        """
        if not self.client:
            return None
        
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment failed: {str(e)}")
            return None
