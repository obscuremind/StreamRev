"""Created / custom channels (stream_type 2 = created_live, 5 = created_vod)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.domain.models import ServerStream, Stream, StreamCategory


class ChannelService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _channel_query(self):
        return self.db.query(Stream).filter(
            or_(Stream.stream_type == 2, Stream.stream_type == 5)
        )

    def get_created_channels(
        self,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict[str, Any]:
        query = self._channel_query()
        total = query.count()
        items = (
            query.order_by(Stream.order.asc(), Stream.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def create_channel(self, data: Dict[str, Any]) -> Stream:
        payload = dict(data)
        if payload.get("stream_type") not in (2, 5):
            payload["stream_type"] = 2
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

    def update_channel(self, stream_id: int, data: Dict[str, Any]) -> Optional[Stream]:
        stream = self._channel_query().filter(Stream.id == stream_id).first()
        if not stream:
            return None
        payload = dict(data)
        if "stream_type" in payload and payload["stream_type"] not in (2, 5):
            payload.pop("stream_type")
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
        if stream.stream_type not in (2, 5):
            stream.stream_type = 2
        self.db.commit()
        self.db.refresh(stream)
        return stream

    def delete_channel(self, stream_id: int) -> bool:
        stream = self._channel_query().filter(Stream.id == stream_id).first()
        if not stream:
            return False
        self.db.query(ServerStream).filter(ServerStream.stream_id == stream_id).delete()
        self.db.delete(stream)
        self.db.commit()
        return True

    def mass_update(self, stream_ids: List[int], data: Dict[str, Any]) -> int:
        if not stream_ids:
            return 0
        payload = dict(data)
        if "stream_type" in payload and payload["stream_type"] not in (2, 5):
            payload.pop("stream_type")
        if isinstance(payload.get("stream_source"), list):
            payload["stream_source"] = json.dumps(payload["stream_source"])
        streams = (
            self._channel_query()
            .filter(Stream.id.in_(stream_ids))
            .all()
        )
        for stream in streams:
            for key, value in payload.items():
                if hasattr(stream, key):
                    setattr(stream, key, value)
            if stream.stream_type not in (2, 5):
                stream.stream_type = 2
        self.db.commit()
        return len(streams)

    def mass_delete(self, stream_ids: List[int]) -> int:
        if not stream_ids:
            return 0
        ch_ids = [
            row[0]
            for row in self.db.query(Stream.id)
            .filter(
                Stream.id.in_(stream_ids),
                or_(Stream.stream_type == 2, Stream.stream_type == 5),
            )
            .all()
        ]
        if not ch_ids:
            return 0
        self.db.query(ServerStream).filter(
            ServerStream.stream_id.in_(ch_ids)
        ).delete(synchronize_session="fetch")
        count = (
            self.db.query(Stream)
            .filter(Stream.id.in_(ch_ids))
            .delete(synchronize_session="fetch")
        )
        self.db.commit()
        return count
