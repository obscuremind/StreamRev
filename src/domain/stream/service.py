"""Live stream domain service: CRUD, sources (JSON), batch ops, stats."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.domain.models import ServerStream, Stream, StreamCategory


class StreamService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(
        self,
        category_id: Optional[int] = None,
        stream_type: Optional[int] = None,
        enabled: Optional[bool] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict[str, Any]:
        query = self.db.query(Stream)
        if category_id is not None:
            query = query.filter(Stream.category_id == category_id)
        if stream_type is not None:
            query = query.filter(Stream.stream_type == stream_type)
        if enabled is not None:
            query = query.filter(Stream.enabled == enabled)
        total = query.count()
        items = (
            query.order_by(Stream.order.asc(), Stream.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def get_by_id(self, stream_id: int) -> Optional[Stream]:
        return self.db.query(Stream).filter(Stream.id == stream_id).first()

    def create(self, data: Dict[str, Any]) -> Stream:
        payload = dict(data)
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

    def update(self, stream_id: int, data: Dict[str, Any]) -> Optional[Stream]:
        stream = self.get_by_id(stream_id)
        if not stream:
            return None
        payload = dict(data)
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

    def delete(self, stream_id: int) -> bool:
        stream = self.get_by_id(stream_id)
        if not stream:
            return False
        self.db.query(ServerStream).filter(ServerStream.stream_id == stream_id).delete()
        self.db.delete(stream)
        self.db.commit()
        return True

    def toggle_status(self, stream_id: int) -> Optional[Stream]:
        stream = self.get_by_id(stream_id)
        if not stream:
            return None
        stream.enabled = not stream.enabled
        self.db.commit()
        self.db.refresh(stream)
        return stream

    def get_sources(self, stream_id: int) -> List[str]:
        stream = self.get_by_id(stream_id)
        if not stream or not stream.stream_source:
            return []
        try:
            parsed = json.loads(stream.stream_source)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
            return [str(parsed)]
        except (json.JSONDecodeError, TypeError):
            return [stream.stream_source] if stream.stream_source else []

    def get_live_streams(self, category_id: Optional[int] = None) -> List[Stream]:
        q = self.db.query(Stream).filter(
            Stream.stream_type == 1,
            Stream.enabled.is_(True),
        )
        if category_id is not None:
            q = q.filter(Stream.category_id == category_id)
        return q.order_by(Stream.order.asc(), Stream.id.asc()).all()

    def search(self, term: str, limit: int = 50) -> List[Stream]:
        t = (term or "").strip()
        if not t:
            return []
        like = f"%{t}%"
        q = self.db.query(Stream).filter(
            or_(
                Stream.stream_display_name.ilike(like),
                Stream.epg_channel_id.ilike(like),
            )
        )
        if t.isdigit():
            q = self.db.query(Stream).filter(
                or_(
                    Stream.stream_display_name.ilike(like),
                    Stream.epg_channel_id.ilike(like),
                    Stream.id == int(t),
                )
            )
        return q.order_by(Stream.id.desc()).limit(limit).all()

    def get_stats(self) -> Dict[str, int]:
        return {
            "total": self.db.query(func.count(Stream.id)).scalar() or 0,
            "live": self.db.query(func.count(Stream.id))
            .filter(Stream.stream_type == 1)
            .scalar()
            or 0,
            "movies": self.db.query(func.count(Stream.id))
            .filter(Stream.stream_type == 3)
            .scalar()
            or 0,
            "radio": self.db.query(func.count(Stream.id))
            .filter(Stream.stream_type == 4)
            .scalar()
            or 0,
            "enabled": self.db.query(func.count(Stream.id))
            .filter(Stream.enabled.is_(True))
            .scalar()
            or 0,
            "disabled": self.db.query(func.count(Stream.id))
            .filter(Stream.enabled.is_(False))
            .scalar()
            or 0,
        }

    def batch_toggle(self, stream_ids: List[int], enabled: bool) -> int:
        if not stream_ids:
            return 0
        count = (
            self.db.query(Stream)
            .filter(Stream.id.in_(stream_ids))
            .update({Stream.enabled: enabled}, synchronize_session="fetch")
        )
        self.db.commit()
        return count

    def batch_delete(self, stream_ids: List[int]) -> int:
        if not stream_ids:
            return 0
        self.db.query(ServerStream).filter(
            ServerStream.stream_id.in_(stream_ids)
        ).delete(synchronize_session="fetch")
        count = (
            self.db.query(Stream)
            .filter(Stream.id.in_(stream_ids))
            .delete(synchronize_session="fetch")
        )
        self.db.commit()
        return count

    def batch_move_category(self, stream_ids: List[int], category_id: int) -> int:
        if not stream_ids:
            return 0
        if (
            self.db.query(StreamCategory).filter(StreamCategory.id == category_id).first()
            is None
        ):
            raise ValueError("category_id does not exist")
        count = (
            self.db.query(Stream)
            .filter(Stream.id.in_(stream_ids))
            .update({Stream.category_id: category_id}, synchronize_session="fetch")
        )
        self.db.commit()
        return count
