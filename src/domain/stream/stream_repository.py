"""Lower-level stream persistence queries."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.models import Stream, StreamLog


class StreamRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_by_id(self, stream_id: int) -> Optional[Stream]:
        return self.db.query(Stream).filter(Stream.id == stream_id).first()

    def find_all(self) -> List[Stream]:
        return self.db.query(Stream).order_by(Stream.order.asc(), Stream.id.asc()).all()

    def find_by_category(self, category_id: int) -> List[Stream]:
        return (
            self.db.query(Stream)
            .filter(Stream.category_id == category_id)
            .order_by(Stream.order.asc(), Stream.id.asc())
            .all()
        )

    def find_enabled(self) -> List[Stream]:
        return (
            self.db.query(Stream)
            .filter(Stream.enabled.is_(True))
            .order_by(Stream.order.asc(), Stream.id.asc())
            .all()
        )

    def find_by_type(self, stream_type: int) -> List[Stream]:
        return (
            self.db.query(Stream)
            .filter(Stream.stream_type == stream_type)
            .order_by(Stream.order.asc(), Stream.id.asc())
            .all()
        )

    def count_by_type(self, stream_type: int) -> int:
        return (
            self.db.query(func.count(Stream.id))
            .filter(Stream.stream_type == stream_type)
            .scalar()
            or 0
        )

    def count_enabled(self) -> int:
        return (
            self.db.query(func.count(Stream.id))
            .filter(Stream.enabled.is_(True))
            .scalar()
            or 0
        )

    def count_total(self) -> int:
        return self.db.query(func.count(Stream.id)).scalar() or 0

    def get_stream_errors(self, stream_id: int) -> List[StreamLog]:
        return (
            self.db.query(StreamLog)
            .filter(
                StreamLog.stream_id == stream_id,
                StreamLog.log_type == "error",
            )
            .order_by(StreamLog.date.desc())
            .all()
        )

    def get_stream_config(self, stream_id: int) -> Optional[Dict[str, Any]]:
        stream = self.find_by_id(stream_id)
        if not stream:
            return None

        def _dt(v: Any) -> Optional[str]:
            if v is None:
                return None
            if hasattr(v, "isoformat"):
                return v.isoformat()
            return str(v)

        return {
            "id": stream.id,
            "stream_display_name": stream.stream_display_name,
            "stream_source": stream.stream_source,
            "stream_icon": stream.stream_icon,
            "epg_channel_id": stream.epg_channel_id,
            "added": _dt(stream.added),
            "category_id": stream.category_id,
            "custom_ffmpeg": stream.custom_ffmpeg,
            "custom_sid": stream.custom_sid,
            "stream_all": stream.stream_all,
            "stream_type": stream.stream_type,
            "target_container": stream.target_container,
            "enabled": stream.enabled,
            "direct_source": stream.direct_source,
            "notes": stream.notes,
            "read_native": stream.read_native,
            "allow_record": stream.allow_record,
            "probed_resolution": stream.probed_resolution,
            "current_source": stream.current_source,
            "tv_archive": stream.tv_archive,
            "tv_archive_duration": stream.tv_archive_duration,
            "tv_archive_server_id": stream.tv_archive_server_id,
            "order": stream.order,
        }
