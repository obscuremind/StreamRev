"""Stream queue admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.stream.queue_service import QueueService
from .dependencies import get_current_admin

router = APIRouter(prefix="/queue", tags=["Admin Queue"])


class QueueAddRequest(BaseModel):
    stream_id: int
    server_id: int
    priority: int = 0


class QueueClearRequest(BaseModel):
    status: Optional[str] = None


@router.get("")
def list_queue(
    page: int = 1,
    per_page: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return QueueService(db).get_all(status=status, page=page, per_page=per_page)


@router.post("/add")
def add_to_queue(
    data: QueueAddRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return QueueService(db).add(
        stream_id=data.stream_id, server_id=data.server_id, priority=data.priority
    )


@router.post("/remove/{queue_id}")
def remove_from_queue(
    queue_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not QueueService(db).remove(queue_id):
        raise HTTPException(status_code=404, detail="Queue entry not found")
    return {"status": "removed"}


@router.post("/retry/{queue_id}")
def retry_queue_entry(
    queue_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = QueueService(db).retry(queue_id)
    if not result:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    return result


@router.post("/clear")
def clear_queue(
    data: QueueClearRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = QueueService(db).clear(status=data.status)
    return {"status": "cleared", "count": count}


@router.get("/stats")
def queue_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return QueueService(db).get_stats()
