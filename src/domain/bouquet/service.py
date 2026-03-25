"""Bouquet domain service: CRUD and JSON-backed ID lists."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.models import Bouquet


class BouquetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> List[Bouquet]:
        return self.db.query(Bouquet).order_by(Bouquet.bouquet_order.asc()).all()

    def get_by_id(self, bouquet_id: int) -> Optional[Bouquet]:
        return self.db.query(Bouquet).filter(Bouquet.id == bouquet_id).first()

    def _encode_json_lists(self, data: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(data)
        for field in (
            "bouquet_channels",
            "bouquet_movies",
            "bouquet_radios",
            "bouquet_series",
        ):
            if isinstance(out.get(field), list):
                out[field] = json.dumps(out[field])
        return out

    def create(self, data: Dict[str, Any]) -> Bouquet:
        payload = self._encode_json_lists(data)
        bouquet = Bouquet(**payload)
        self.db.add(bouquet)
        self.db.commit()
        self.db.refresh(bouquet)
        return bouquet

    def update(self, bouquet_id: int, data: Dict[str, Any]) -> Optional[Bouquet]:
        bouquet = self.get_by_id(bouquet_id)
        if not bouquet:
            return None
        payload = self._encode_json_lists(data)
        for key, value in payload.items():
            if hasattr(bouquet, key):
                setattr(bouquet, key, value)
        self.db.commit()
        self.db.refresh(bouquet)
        return bouquet

    def delete(self, bouquet_id: int) -> bool:
        bouquet = self.get_by_id(bouquet_id)
        if not bouquet:
            return False
        self.db.delete(bouquet)
        self.db.commit()
        return True

    @staticmethod
    def get_channel_ids(bouquet: Bouquet) -> List[int]:
        try:
            raw = json.loads(bouquet.bouquet_channels or "[]")
            return [int(x) for x in raw] if isinstance(raw, list) else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    @staticmethod
    def get_movie_ids(bouquet: Bouquet) -> List[int]:
        try:
            raw = json.loads(bouquet.bouquet_movies or "[]")
            return [int(x) for x in raw] if isinstance(raw, list) else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    @staticmethod
    def get_series_ids(bouquet: Bouquet) -> List[int]:
        try:
            raw = json.loads(bouquet.bouquet_series or "[]")
            return [int(x) for x in raw] if isinstance(raw, list) else []
        except (json.JSONDecodeError, TypeError, ValueError):
            return []
