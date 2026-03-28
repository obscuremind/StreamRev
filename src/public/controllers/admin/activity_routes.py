"""User activity admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.activity.service import ActivityService
from .dependencies import get_current_admin

router = APIRouter(prefix="/activity", tags=["Admin Activity"])


class CleanupRequest(BaseModel):
    days: int = 30


@router.get("")
def list_activity(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ActivityService(db).get_all(page=page, per_page=per_page)


@router.get("/stats")
def activity_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ActivityService(db).get_stats()


@router.get("/{activity_id}")
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = ActivityService(db).get_by_id(activity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Activity not found")
    return result


@router.get("/user/{user_id}")
def user_activity(
    user_id: int,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ActivityService(db).get_by_user(user_id, page=page, per_page=per_page)


@router.get("/ip-history/{user_id}")
def ip_history(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"history": ActivityService(db).get_ip_history(user_id)}


@router.get("/stream/{stream_id}")
def stream_activity(
    stream_id: int,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ActivityService(db).get_by_stream(stream_id, page=page, per_page=per_page)


@router.delete("/cleanup")
def cleanup_activity(
    data: CleanupRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = ActivityService(db).cleanup(days=data.days)
    return {"status": "cleaned", "count": count}
