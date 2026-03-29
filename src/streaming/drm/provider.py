from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

import httpx

from src.core.config import settings


class DRMProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class DRMKey:
    kid: str
    key: str


class DRMProvider:
    def _static_keys(self) -> Dict[int, List[DRMKey]]:
        raw = settings.DRM_STATIC_KEYS_JSON.strip()
        if not raw:
            return {}
        parsed = json.loads(raw)
        out: Dict[int, List[DRMKey]] = {}
        for sid, rows in parsed.items():
            out[int(sid)] = [DRMKey(kid=str(r["kid"]), key=str(r["key"])) for r in rows]
        return out

    async def get_keys(self, stream_id: int, username: str) -> List[DRMKey]:
        mode = settings.DRM_PROVIDER_MODE.lower()
        if mode == "off":
            return []

        if mode == "static":
            return self._static_keys().get(stream_id, [])

        if mode == "http":
            if not settings.DRM_PROVIDER_URL:
                raise DRMProviderError("DRM_PROVIDER_URL is empty")
            headers = {}
            if settings.DRM_PROVIDER_TOKEN:
                headers["Authorization"] = f"Bearer {settings.DRM_PROVIDER_TOKEN}"
            payload = {"stream_id": stream_id, "username": username}
            async with httpx.AsyncClient(timeout=settings.DRM_PROVIDER_TIMEOUT_SECONDS) as client:
                resp = await client.post(settings.DRM_PROVIDER_URL, json=payload, headers=headers)
                if resp.status_code >= 400:
                    raise DRMProviderError(f"provider status={resp.status_code}")
                data = resp.json()
                keys = data.get("keys", [])
                return [DRMKey(kid=str(row["kid"]), key=str(row["key"])) for row in keys]

        raise DRMProviderError(f"Unsupported DRM provider mode: {mode}")


drm_provider = DRMProvider()
