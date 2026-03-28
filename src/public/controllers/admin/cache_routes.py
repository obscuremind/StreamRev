"""Cache management admin routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.core.cache.redis_cache import cache
from src.domain.models import User
from .dependencies import get_current_admin

router = APIRouter(prefix="/cache", tags=["Admin Cache"])


class FlushPatternRequest(BaseModel):
    pattern: str


@router.get("")
async def cache_overview(
    admin: User = Depends(get_current_admin),
):
    try:
        info = await cache.info()
    except Exception:
        info = {"status": "unavailable"}
    return {"cache": info}


@router.get("/keys")
async def cache_keys(
    pattern: str = "*",
    limit: int = 100,
    admin: User = Depends(get_current_admin),
):
    try:
        keys = await cache.keys(pattern)
        return {"keys": keys[:limit], "total": len(keys)}
    except Exception:
        return {"keys": [], "total": 0, "error": "Cache unavailable"}


@router.get("/key/{key:path}")
async def get_cache_key(
    key: str,
    admin: User = Depends(get_current_admin),
):
    try:
        value = await cache.get(key)
        return {"key": key, "value": value}
    except Exception:
        return {"key": key, "value": None, "error": "Cache unavailable"}


@router.delete("/key/{key:path}")
async def delete_cache_key(
    key: str,
    admin: User = Depends(get_current_admin),
):
    try:
        await cache.delete(key)
        return {"status": "deleted", "key": key}
    except Exception:
        return {"status": "error", "error": "Cache unavailable"}


@router.post("/flush")
async def flush_cache(
    admin: User = Depends(get_current_admin),
):
    try:
        await cache.flush()
        return {"status": "flushed"}
    except Exception:
        return {"status": "error", "error": "Cache unavailable"}


@router.post("/flush-pattern")
async def flush_pattern(
    data: FlushPatternRequest,
    admin: User = Depends(get_current_admin),
):
    try:
        keys = await cache.keys(data.pattern)
        count = 0
        for key in keys:
            await cache.delete(key)
            count += 1
        return {"status": "flushed", "pattern": data.pattern, "count": count}
    except Exception:
        return {"status": "error", "error": "Cache unavailable"}


@router.get("/stats")
async def cache_stats(
    admin: User = Depends(get_current_admin),
):
    try:
        info = await cache.info()
        return {
            "connected": True,
            "info": info,
        }
    except Exception:
        return {"connected": False, "info": {}}
