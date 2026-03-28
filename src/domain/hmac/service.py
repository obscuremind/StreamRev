"""HMAC key management service."""

from __future__ import annotations

import hashlib
import hmac as hmac_lib
import secrets
import time
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.models import HmacKey


class HmacKeyService:
    """Manages HMAC keys for API authentication."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> List[Dict[str, Any]]:
        items = self.db.query(HmacKey).order_by(HmacKey.id.asc()).all()
        return [self._to_dict(k) for k in items]

    def get_by_id(self, key_id: int) -> Optional[Dict[str, Any]]:
        k = self.db.query(HmacKey).filter(HmacKey.id == key_id).first()
        if not k:
            return None
        return self._to_dict(k)

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        key_value = data.get("key") or secrets.token_hex(32)
        entry = HmacKey(
            key=key_value,
            notes=data.get("notes"),
            enabled=data.get("enabled", True),
            allowed_ips=data.get("allowed_ips"),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return self._to_dict(entry)

    def update(self, key_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        k = self.db.query(HmacKey).filter(HmacKey.id == key_id).first()
        if not k:
            return None
        for attr, value in data.items():
            if hasattr(k, attr):
                setattr(k, attr, value)
        self.db.commit()
        self.db.refresh(k)
        return self._to_dict(k)

    def delete(self, key_id: int) -> bool:
        k = self.db.query(HmacKey).filter(HmacKey.id == key_id).first()
        if not k:
            return False
        self.db.delete(k)
        self.db.commit()
        return True

    def toggle(self, key_id: int) -> Optional[Dict[str, Any]]:
        k = self.db.query(HmacKey).filter(HmacKey.id == key_id).first()
        if not k:
            return None
        k.enabled = not k.enabled
        self.db.commit()
        self.db.refresh(k)
        return self._to_dict(k)

    def generate_signature(self, key_id: int, message: str) -> Optional[Dict[str, Any]]:
        k = self.db.query(HmacKey).filter(HmacKey.id == key_id).first()
        if not k or not k.enabled:
            return None
        timestamp = str(int(time.time()))
        data_to_sign = f"{message}{timestamp}"
        signature = hmac_lib.new(
            k.key.encode("utf-8"), data_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return {"signature": signature, "timestamp": timestamp, "key_id": key_id}

    @staticmethod
    def _to_dict(k: HmacKey) -> Dict[str, Any]:
        return {
            "id": k.id,
            "key": k.key,
            "notes": k.notes,
            "enabled": k.enabled,
            "allowed_ips": k.allowed_ips,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }
