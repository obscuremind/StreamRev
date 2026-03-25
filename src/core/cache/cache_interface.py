from abc import ABC, abstractmethod
from typing import Optional, Any


class CacheInterface(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def flush(self) -> bool:
        pass

    @abstractmethod
    async def incr(self, key: str) -> int:
        pass

    @abstractmethod
    async def expire(self, key: str, ttl: int) -> bool:
        pass
