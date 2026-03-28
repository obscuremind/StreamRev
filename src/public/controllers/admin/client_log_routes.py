"""Client log admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional

from src.core.database import get_db
from src.domain.models import ClientLog, User
from .dependencies import get_current_admin

router = APIRouter(prefix="/client-logs", tags=["Admin Client Logs"])


class CleanupRequest(BaseModel):
    days: int = 30


@router.get("")
def list_client_logs(
    page: int = 1,
    per_page: int = 50,
    user_id: Optional[int] = None,
    event: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = db.query(ClientLog)
    if user_id is not None:
        query = query.filter(ClientLog.user_id == user_id)
    if event:
        query = query.filter(ClientLog.event == event)
    total = query.count()
    items = (
        query.order_by(ClientLog.date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_log_to_dict(l) for l in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/events")
def list_event_types(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    events = (
        db.query(ClientLog.event, func.count(ClientLog.id).label("count"))
        .group_by(ClientLog.event)
        .order_by(func.count(ClientLog.id).desc())
        .all()
    )
    return {"events": [{"event": e.event, "count": e.count} for e in events]}


@router.get("/{log_id}")
def get_client_log(
    log_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    log = db.query(ClientLog).filter(ClientLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return _log_to_dict(log)


@router.delete("/cleanup")
def cleanup_logs(
    data: CleanupRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    cutoff = datetime.utcnow() - timedelta(days=data.days)
    count = db.query(ClientLog).filter(ClientLog.date < cutoff).delete(synchronize_session="fetch")
    db.commit()
    return {"status": "cleaned", "count": count}


def _log_to_dict(log: ClientLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "stream_id": log.stream_id,
        "event": log.event,
        "ip": log.ip,
        "data": log.data,
        "date": log.date.isoformat() if log.date else None,
    }
