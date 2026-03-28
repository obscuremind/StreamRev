"""Recording service for managing scheduled and archived recordings."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.models import ScheduledRecording


class RecordingService:
    """Manages stream recordings (scheduled, active, archived)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        query = self.db.query(ScheduledRecording)
        total = query.count()
        items = (
            query.order_by(ScheduledRecording.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": [self._to_dict(r) for r in items], "total": total, "page": page, "per_page": per_page}

    def get_scheduled(self) -> List[Dict[str, Any]]:
        items = (
            self.db.query(ScheduledRecording)
            .filter(ScheduledRecording.status.in_(["scheduled", "pending"]))
            .order_by(ScheduledRecording.start_time.asc())
            .all()
        )
        return [self._to_dict(r) for r in items]

    def get_archived(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        query = self.db.query(ScheduledRecording).filter(ScheduledRecording.status == "archived")
        total = query.count()
        items = (
            query.order_by(ScheduledRecording.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": [self._to_dict(r) for r in items], "total": total, "page": page, "per_page": per_page}

    def get_disk_usage(self) -> Dict[str, Any]:
        total_size = self.db.query(func.sum(ScheduledRecording.file_size)).scalar() or 0
        total_count = self.db.query(func.count(ScheduledRecording.id)).scalar() or 0
        return {"total_size_bytes": total_size, "total_recordings": total_count}

    def schedule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        recording = ScheduledRecording(
            stream_id=data["stream_id"],
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            title=data.get("title", ""),
            status="scheduled",
            output_path=data.get("output_path"),
            created_at=datetime.utcnow(),
        )
        self.db.add(recording)
        self.db.commit()
        self.db.refresh(recording)
        return self._to_dict(recording)

    def delete_scheduled(self, recording_id: int) -> bool:
        r = self.db.query(ScheduledRecording).filter(ScheduledRecording.id == recording_id).first()
        if not r:
            return False
        self.db.delete(r)
        self.db.commit()
        return True

    def archive(self, recording_id: int) -> Optional[Dict[str, Any]]:
        r = self.db.query(ScheduledRecording).filter(ScheduledRecording.id == recording_id).first()
        if not r:
            return None
        r.status = "archived"
        self.db.commit()
        self.db.refresh(r)
        return self._to_dict(r)

    @staticmethod
    def _to_dict(r: ScheduledRecording) -> Dict[str, Any]:
        return {
            "id": r.id,
            "stream_id": r.stream_id,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "end_time": r.end_time.isoformat() if r.end_time else None,
            "title": r.title,
            "status": r.status,
            "output_path": r.output_path,
            "file_size": r.file_size,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
