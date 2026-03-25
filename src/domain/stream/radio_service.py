"""Radio streams (stream_type == 4)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.models import ServerStream, Stream, StreamCategory


class RadioService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _radio_query(self):
        return self.db.query(Stream).filter(Stream.stream_type == 4)

    def get_all_radios(
        self,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict[str, Any]:
        query = self._radio_query()
        total = query.count()
        items = (
            query.order_by(Stream.order.asc(), Stream.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def create_radio(self, data: Dict[str, Any]) -> Stream:
        payload = dict(data)
        payload["stream_type"] = 4
        if isinstance(payload.get("stream_source"), list):
            payload["stream_source"] = json.dumps(payload["stream_source"])
        cid = payload.get("category_id")
        if cid is not None and (
            self.db.query(StreamCategory).filter(StreamCategory.id == cid).first()
            is None
        ):
            raise ValueError("category_id does not exist")
        stream = Stream(**payload)
        self.db.add(stream)
        self.db.commit()
        self.db.refresh(stream)
        return stream

    def update_radio(self, stream_id: int, data: Dict[str, Any]) -> Optional[Stream]:
        stream = self._radio_query().filter(Stream.id == stream_id).first()
        if not stream:
            return None
        payload = dict(data)
        payload["stream_type"] = 4
        if isinstance(payload.get("stream_source"), list):
            payload["stream_source"] = json.dumps(payload["stream_source"])
        cid = payload.get("category_id")
        if cid is not None and (
            self.db.query(StreamCategory).filter(StreamCategory.id == cid).first()
            is None
        ):
            raise ValueError("category_id does not exist")
        for key, value in payload.items():
            if hasattr(stream, key):
                setattr(stream, key, value)
        self.db.commit()
        self.db.refresh(stream)
        return stream

    def delete_radio(self, stream_id: int) -> bool:
        stream = self._radio_query().filter(Stream.id == stream_id).first()
        if not stream:
            return False
        self.db.query(ServerStream).filter(ServerStream.stream_id == stream_id).delete()
        self.db.delete(stream)
        self.db.commit()
        return True

    def get_radio_categories(self) -> List[StreamCategory]:
        return (
            self.db.query(StreamCategory)
            .filter(StreamCategory.category_type == "radio")
            .order_by(StreamCategory.order.asc(), StreamCategory.id.asc())
            .all()
        )
