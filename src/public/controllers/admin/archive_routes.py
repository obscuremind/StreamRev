"""Archive/Catchup/Timeshift admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.archive.service import ArchiveService
from .dependencies import get_current_admin

router = APIRouter(prefix="/archive", tags=["Admin Archive/Catchup"])


class EnableArchiveRequest(BaseModel):
    duration: int = 7
    server_id: Optional[int] = None


class CleanupAllRequest(BaseModel):
    days: Optional[int] = None


@router.get("/streams")
def list_archive_streams(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ArchiveService(db).get_archive_streams(page=page, per_page=per_page)


@router.get("/stream/{stream_id}")
def get_stream_archive(
    stream_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = ArchiveService(db).get_stream_archive(stream_id)
    if not result:
        raise HTTPException(status_code=404, detail="Stream not found")
    return result


@router.get("/stream/{stream_id}/segments")
def get_stream_segments(
    stream_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ArchiveService(db).get_stream_segments(stream_id)


@router.post("/enable/{stream_id}")
def enable_archive(
    stream_id: int,
    data: EnableArchiveRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = ArchiveService(db).enable_archive(stream_id, duration=data.duration, server_id=data.server_id)
    if not result:
        raise HTTPException(status_code=404, detail="Stream not found")
    return result


@router.post("/disable/{stream_id}")
def disable_archive(
    stream_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = ArchiveService(db).disable_archive(stream_id)
    if not result:
        raise HTTPException(status_code=404, detail="Stream not found")
    return result


@router.post("/cleanup/{stream_id}")
def cleanup_stream_archive(
    stream_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ArchiveService(db).cleanup_stream(stream_id)


@router.get("/stats")
def archive_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ArchiveService(db).get_stats()


@router.post("/cleanup-all")
def cleanup_all_archives(
    data: CleanupAllRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ArchiveService(db).cleanup_all(days=data.days)
