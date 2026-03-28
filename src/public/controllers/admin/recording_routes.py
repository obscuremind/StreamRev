"""Recording management admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from src.core.database import get_db
from src.domain.models import User
from src.domain.recording.service import RecordingService
from .dependencies import get_current_admin

router = APIRouter(prefix="/recordings", tags=["Admin Recordings"])


class ScheduleRequest(BaseModel):
    stream_id: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    title: str = ""
    output_path: Optional[str] = None


@router.get("")
def list_recordings(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return RecordingService(db).get_all(page=page, per_page=per_page)


@router.get("/scheduled")
def list_scheduled(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"scheduled": RecordingService(db).get_scheduled()}


@router.get("/archive")
def list_archived(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return RecordingService(db).get_archived(page=page, per_page=per_page)


@router.get("/disk-usage")
def disk_usage(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return RecordingService(db).get_disk_usage()


@router.post("/schedule")
def schedule_recording(
    data: ScheduleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    payload = data.model_dump(exclude_none=True)
    for field in ("start_time", "end_time"):
        if field in payload and isinstance(payload[field], str):
            try:
                payload[field] = datetime.fromisoformat(payload[field])
            except ValueError:
                pass
    return RecordingService(db).schedule(payload)


@router.delete("/scheduled/{recording_id}")
def delete_scheduled(
    recording_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not RecordingService(db).delete_scheduled(recording_id):
        raise HTTPException(status_code=404, detail="Recording not found")
    return {"status": "deleted"}


@router.post("/archive/{recording_id}")
def archive_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = RecordingService(db).archive(recording_id)
    if not result:
        raise HTTPException(status_code=404, detail="Recording not found")
    return result
