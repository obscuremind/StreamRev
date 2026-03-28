"""Session management admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict, List

from src.core.database import get_db
from src.domain.models import Line, User
from .dependencies import get_current_admin

router = APIRouter(prefix="/sessions", tags=["Admin Sessions"])


@router.get("")
def list_sessions(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = db.query(Line)
    total = query.count()
    items = (
        query.order_by(Line.date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_session_to_dict(l) for l in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/current")
def current_sessions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    items = db.query(Line).order_by(Line.date.desc()).limit(100).all()
    return {"sessions": [_session_to_dict(l) for l in items], "total": len(items)}


@router.post("/{line_id}/revoke")
def revoke_session(
    line_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    line = db.query(Line).filter(Line.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(line)
    db.commit()
    return {"status": "revoked", "line_id": line_id}


@router.post("/revoke-all")
def revoke_all_sessions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = db.query(Line).delete(synchronize_session="fetch")
    db.commit()
    return {"status": "all_revoked", "count": count}


def _session_to_dict(line: Line) -> Dict[str, Any]:
    return {
        "id": line.id,
        "user_id": line.user_id,
        "stream_id": line.stream_id,
        "server_id": line.server_id,
        "ip": line.user_ip,
        "user_agent": line.user_agent,
        "container": line.container,
        "country": line.geoip_country_code,
        "date": line.date.isoformat() if line.date else None,
    }
