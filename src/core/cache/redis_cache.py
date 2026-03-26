import json
import redis.asyncio as aioredis
from typing import Optional, Any
from .cache_interface import CacheInterface
from src.core.config import settings


class RedisCache(CacheInterface):
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self):
        self._redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )

    async def disconnect(self):
        if self._redis:
            await self._redis.close()

    @property
    def redis(self) -> aioredis.Redis:
        if not self._redis:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await self.redis.set(key, value, ex=ttl)

    async def delete(self, key: str) -> bool:
        return bool(await self.redis.delete(key))

    async def exists(self, key: str) -> bool:
        return bool(await self.redis.exists(key))

    async def flush(self) -> bool:
        return await self.redis.flushdb()

    async def incr(self, key: str) -> int:
        return await self.redis.incr(key)

    async def expire(self, key: str, ttl: int) -> bool:
        return await self.redis.expire(key, ttl)

    async def hset(self, name: str, key: str, value: Any) -> int:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        return await self.redis.hset(name, key, value)

    async def hget(self, name: str, key: str) -> Optional[Any]:
        value = await self.redis.hget(name, key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def hgetall(self, name: str) -> dict:
        return await self.redis.hgetall(name)


cache = RedisCache()
