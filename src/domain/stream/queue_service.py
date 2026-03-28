"""Stream queue service for managing stream start/stop queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.models import StreamQueue


class QueueService:
    """Manages the stream processing queue."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(
        self,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict[str, Any]:
        query = self.db.query(StreamQueue)
        if status:
            query = query.filter(StreamQueue.status == status)
        total = query.count()
        items = (
            query.order_by(StreamQueue.priority.desc(), StreamQueue.created_at.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": [self._to_dict(q) for q in items], "total": total, "page": page, "per_page": per_page}

    def add(self, stream_id: int, server_id: int, priority: int = 0) -> Dict[str, Any]:
        entry = StreamQueue(
            stream_id=stream_id,
            server_id=server_id,
            status="pending",
            priority=priority,
            created_at=datetime.utcnow(),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return self._to_dict(entry)

    def remove(self, queue_id: int) -> bool:
        entry = self.db.query(StreamQueue).filter(StreamQueue.id == queue_id).first()
        if not entry:
            return False
        self.db.delete(entry)
        self.db.commit()
        return True

    def retry(self, queue_id: int) -> Optional[Dict[str, Any]]:
        entry = self.db.query(StreamQueue).filter(StreamQueue.id == queue_id).first()
        if not entry:
            return None
        entry.status = "pending"
        entry.error_message = None
        entry.started_at = None
        entry.completed_at = None
        self.db.commit()
        self.db.refresh(entry)
        return self._to_dict(entry)

    def clear(self, status: Optional[str] = None) -> int:
        query = self.db.query(StreamQueue)
        if status:
            query = query.filter(StreamQueue.status == status)
        count = query.delete(synchronize_session="fetch")
        self.db.commit()
        return count

    def get_stats(self) -> Dict[str, Any]:
        total = self.db.query(func.count(StreamQueue.id)).scalar() or 0
        pending = self.db.query(func.count(StreamQueue.id)).filter(StreamQueue.status == "pending").scalar() or 0
        processing = self.db.query(func.count(StreamQueue.id)).filter(StreamQueue.status == "processing").scalar() or 0
        completed = self.db.query(func.count(StreamQueue.id)).filter(StreamQueue.status == "completed").scalar() or 0
        failed = self.db.query(func.count(StreamQueue.id)).filter(StreamQueue.status == "failed").scalar() or 0
        return {
            "total": total,
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed,
        }

    @staticmethod
    def _to_dict(entry: StreamQueue) -> Dict[str, Any]:
        return {
            "id": entry.id,
            "stream_id": entry.stream_id,
            "server_id": entry.server_id,
            "status": entry.status,
            "priority": entry.priority,
            "error_message": entry.error_message,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "started_at": entry.started_at.isoformat() if entry.started_at else None,
            "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
        }
