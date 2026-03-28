"""Archive/Catchup/Timeshift service for stream archiving."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.models import Stream


class ArchiveService:
    """Manages stream archive/catchup/timeshift functionality."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_archive_streams(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        query = self.db.query(Stream).filter(Stream.tv_archive.is_(True))
        total = query.count()
        items = (
            query.order_by(Stream.id.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {
            "items": [self._stream_to_dict(s) for s in items],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    def get_stream_archive(self, stream_id: int) -> Optional[Dict[str, Any]]:
        s = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not s:
            return None
        return self._stream_to_dict(s)

    def get_stream_segments(self, stream_id: int) -> Dict[str, Any]:
        s = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not s:
            return {"error": "Stream not found"}
        return {
            "stream_id": stream_id,
            "tv_archive": s.tv_archive,
            "duration_days": s.tv_archive_duration,
            "server_id": s.tv_archive_server_id,
            "segments": [],
        }

    def enable_archive(self, stream_id: int, duration: int = 7, server_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        s = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not s:
            return None
        s.tv_archive = True
        s.tv_archive_duration = duration
        if server_id is not None:
            s.tv_archive_server_id = server_id
        self.db.commit()
        self.db.refresh(s)
        return self._stream_to_dict(s)

    def disable_archive(self, stream_id: int) -> Optional[Dict[str, Any]]:
        s = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not s:
            return None
        s.tv_archive = False
        self.db.commit()
        self.db.refresh(s)
        return self._stream_to_dict(s)

    def cleanup_stream(self, stream_id: int) -> Dict[str, Any]:
        s = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not s:
            return {"error": "Stream not found", "cleaned": 0}
        return {"stream_id": stream_id, "cleaned": 0, "status": "ok"}

    def get_stats(self) -> Dict[str, Any]:
        total_archived = self.db.query(func.count(Stream.id)).filter(Stream.tv_archive.is_(True)).scalar() or 0
        total_streams = self.db.query(func.count(Stream.id)).scalar() or 0
        return {
            "total_archived": total_archived,
            "total_streams": total_streams,
            "archive_percentage": round(total_archived / total_streams * 100, 2) if total_streams > 0 else 0,
        }

    def cleanup_all(self, days: Optional[int] = None) -> Dict[str, Any]:
        return {"status": "ok", "cleaned_streams": 0}

    @staticmethod
    def _stream_to_dict(s: Stream) -> Dict[str, Any]:
        return {
            "id": s.id,
            "stream_display_name": s.stream_display_name,
            "tv_archive": s.tv_archive,
            "tv_archive_duration": s.tv_archive_duration,
            "tv_archive_server_id": s.tv_archive_server_id,
            "enabled": s.enabled,
            "category_id": s.category_id,
        }
