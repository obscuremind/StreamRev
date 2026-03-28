"""On-demand stream admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Any, Dict, List

from src.core.database import get_db
from src.domain.models import ServerStream, Stream, User
from .dependencies import get_current_admin

router = APIRouter(prefix="/on-demand", tags=["Admin On-Demand"])


class BatchRequest(BaseModel):
    ids: List[int]


@router.get("")
def list_ondemand(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    items = (
        db.query(ServerStream)
        .filter(ServerStream.on_demand.is_(True))
        .order_by(ServerStream.id.desc())
        .all()
    )
    return {"items": [_ss_to_dict(ss) for ss in items], "total": len(items)}


@router.post("/start/{server_stream_id}")
def start_ondemand(
    server_stream_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ss = db.query(ServerStream).filter(ServerStream.id == server_stream_id).first()
    if not ss:
        raise HTTPException(status_code=404, detail="Server stream not found")
    ss.stream_status = 1
    db.commit()
    db.refresh(ss)
    return {"status": "started", "server_stream": _ss_to_dict(ss)}


@router.post("/stop/{server_stream_id}")
def stop_ondemand(
    server_stream_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ss = db.query(ServerStream).filter(ServerStream.id == server_stream_id).first()
    if not ss:
        raise HTTPException(status_code=404, detail="Server stream not found")
    ss.stream_status = 0
    ss.pid = None
    db.commit()
    db.refresh(ss)
    return {"status": "stopped", "server_stream": _ss_to_dict(ss)}


@router.post("/restart/{server_stream_id}")
def restart_ondemand(
    server_stream_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ss = db.query(ServerStream).filter(ServerStream.id == server_stream_id).first()
    if not ss:
        raise HTTPException(status_code=404, detail="Server stream not found")
    ss.stream_status = 2
    ss.pid = None
    db.commit()
    db.refresh(ss)
    return {"status": "restarting", "server_stream": _ss_to_dict(ss)}


@router.get("/status/{server_stream_id}")
def ondemand_status(
    server_stream_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ss = db.query(ServerStream).filter(ServerStream.id == server_stream_id).first()
    if not ss:
        raise HTTPException(status_code=404, detail="Server stream not found")
    return _ss_to_dict(ss)


@router.post("/start-batch")
def start_batch(
    data: BatchRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = (
        db.query(ServerStream)
        .filter(ServerStream.id.in_(data.ids))
        .update({ServerStream.stream_status: 1}, synchronize_session="fetch")
    )
    db.commit()
    return {"status": "started", "count": count}


@router.post("/stop-batch")
def stop_batch(
    data: BatchRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = (
        db.query(ServerStream)
        .filter(ServerStream.id.in_(data.ids))
        .update({ServerStream.stream_status: 0, ServerStream.pid: None}, synchronize_session="fetch")
    )
    db.commit()
    return {"status": "stopped", "count": count}


@router.get("/active")
def list_active(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    items = (
        db.query(ServerStream)
        .filter(ServerStream.on_demand.is_(True), ServerStream.stream_status == 1)
        .order_by(ServerStream.id.desc())
        .all()
    )
    return {"items": [_ss_to_dict(ss) for ss in items], "total": len(items)}


def _ss_to_dict(ss: ServerStream) -> Dict[str, Any]:
    return {
        "id": ss.id,
        "server_id": ss.server_id,
        "stream_id": ss.stream_id,
        "pid": ss.pid,
        "on_demand": ss.on_demand,
        "stream_status": ss.stream_status,
        "bitrate": ss.bitrate,
        "current_source": ss.current_source,
    }
