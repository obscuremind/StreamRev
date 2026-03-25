import os
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.domain.models import Line, StreamLog, User, UserActivity

from .dependencies import get_current_admin

router = APIRouter(prefix="/logs", tags=["Admin Logs"])


@router.get("/stream")
def stream_logs(
    stream_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = db.query(StreamLog)
    if stream_id:
        query = query.filter(StreamLog.stream_id == stream_id)
    total = query.count()
    items = query.order_by(StreamLog.date.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [
            {
                "id": l.id,
                "stream_id": l.stream_id,
                "server_id": l.server_id,
                "date": str(l.date),
                "info": l.info,
                "type": l.log_type,
            }
            for l in items
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/activity")
def activity_logs(
    user_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = db.query(UserActivity)
    if user_id:
        query = query.filter(UserActivity.user_id == user_id)
    total = query.count()
    items = query.order_by(UserActivity.date_start.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [
            {
                "id": a.id,
                "user_id": a.user_id,
                "stream_id": a.stream_id,
                "server_id": a.server_id,
                "user_ip": a.user_ip,
                "user_agent": a.user_agent,
                "container": a.container,
                "date_start": str(a.date_start),
                "date_stop": str(a.date_stop) if a.date_stop else None,
                "geoip_country_code": a.geoip_country_code,
            }
            for a in items
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/connections")
def connection_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = db.query(Line)
    total = query.count()
    items = query.order_by(Line.date.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [
            {
                "id": l.id,
                "user_id": l.user_id,
                "stream_id": l.stream_id,
                "server_id": l.server_id,
                "container": l.container,
                "user_ip": l.user_ip,
                "user_agent": l.user_agent,
                "date": str(l.date),
                "bitrate": l.bitrate,
            }
            for l in items
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


def _list_log_files():
    log_dir = os.path.join(settings.BASE_DIR, "logs")
    if not os.path.exists(log_dir):
        return []
    return [f for f in os.listdir(log_dir) if f.endswith(".log")]


@router.get("/system")
def system_logs(
    log_file: str = Query("app"),
    lines: int = Query(200),
    admin: User = Depends(get_current_admin),
):
    log_dir = os.path.join(settings.BASE_DIR, "logs")
    safe_name = os.path.basename(log_file)
    log_path = os.path.join(log_dir, safe_name if safe_name.endswith(".log") else safe_name + ".log")
    if not os.path.exists(log_path):
        return {"lines": [], "file": safe_name, "available": _list_log_files()}
    with open(log_path, encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()
    return {
        "lines": all_lines[-lines:],
        "file": safe_name,
        "total_lines": len(all_lines),
        "available": _list_log_files(),
    }
