"""Proxy management service for upstream stream fetching."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.models import Proxy


class ProxyService:
    """Manages HTTP/SOCKS proxies for stream fetching."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> List[Dict[str, Any]]:
        items = self.db.query(Proxy).order_by(Proxy.id.asc()).all()
        return [self._to_dict(p) for p in items]

    def get_by_id(self, proxy_id: int) -> Optional[Dict[str, Any]]:
        p = self.db.query(Proxy).filter(Proxy.id == proxy_id).first()
        if not p:
            return None
        return self._to_dict(p)

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        proxy = Proxy(**data)
        self.db.add(proxy)
        self.db.commit()
        self.db.refresh(proxy)
        return self._to_dict(proxy)

    def update(self, proxy_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        p = self.db.query(Proxy).filter(Proxy.id == proxy_id).first()
        if not p:
            return None
        for key, value in data.items():
            if hasattr(p, key):
                setattr(p, key, value)
        self.db.commit()
        self.db.refresh(p)
        return self._to_dict(p)

    def delete(self, proxy_id: int) -> bool:
        p = self.db.query(Proxy).filter(Proxy.id == proxy_id).first()
        if not p:
            return False
        self.db.delete(p)
        self.db.commit()
        return True

    def test_proxy(self, proxy_id: int) -> Dict[str, Any]:
        p = self.db.query(Proxy).filter(Proxy.id == proxy_id).first()
        if not p:
            return {"success": False, "error": "Proxy not found"}
        if not p.proxy_url:
            return {"success": False, "error": "No proxy URL configured"}
        return {
            "success": True,
            "proxy_id": proxy_id,
            "proxy_url": p.proxy_url,
            "proxy_type": p.proxy_type,
        }

    def toggle(self, proxy_id: int) -> Optional[Dict[str, Any]]:
        p = self.db.query(Proxy).filter(Proxy.id == proxy_id).first()
        if not p:
            return None
        p.enabled = not p.enabled
        self.db.commit()
        self.db.refresh(p)
        return self._to_dict(p)

    @staticmethod
    def _to_dict(p: Proxy) -> Dict[str, Any]:
        return {
            "id": p.id,
            "proxy_name": p.proxy_name,
            "proxy_url": p.proxy_url,
            "proxy_type": p.proxy_type,
            "proxy_username": p.proxy_username,
            "enabled": p.enabled,
            "server_id": p.server_id,
        }
