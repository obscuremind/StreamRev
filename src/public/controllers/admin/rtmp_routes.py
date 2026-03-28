"""RTMP server admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.core.database import get_db
from src.domain.models import Line, ServerStream, Stream, User
from .dependencies import get_current_admin

router = APIRouter(prefix="/rtmp", tags=["Admin RTMP"])


@router.get("")
def list_rtmp_streams(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    items = (
        db.query(ServerStream)
        .join(Stream, ServerStream.stream_id == Stream.id)
        .filter(Stream.target_container == "rtmp")
        .order_by(ServerStream.id.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": ss.id,
                "server_id": ss.server_id,
                "stream_id": ss.stream_id,
                "pid": ss.pid,
                "stream_status": ss.stream_status,
                "bitrate": ss.bitrate,
            }
            for ss in items
        ],
        "total": len(items),
    }


@router.get("/stats")
def rtmp_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    total_rtmp = (
        db.query(func.count(Stream.id))
        .filter(Stream.target_container == "rtmp")
        .scalar()
        or 0
    )
    active_rtmp = (
        db.query(func.count(ServerStream.id))
        .join(Stream, ServerStream.stream_id == Stream.id)
        .filter(Stream.target_container == "rtmp", ServerStream.stream_status == 1)
        .scalar()
        or 0
    )
    return {"total_rtmp_streams": total_rtmp, "active_rtmp": active_rtmp}


@router.get("/publishers")
def list_publishers(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    items = (
        db.query(ServerStream)
        .join(Stream, ServerStream.stream_id == Stream.id)
        .filter(Stream.target_container == "rtmp", ServerStream.stream_status == 1)
        .all()
    )
    return {
        "publishers": [
            {
                "id": ss.id,
                "server_id": ss.server_id,
                "stream_id": ss.stream_id,
                "pid": ss.pid,
                "bitrate": ss.bitrate,
            }
            for ss in items
        ]
    }


@router.post("/{server_stream_id}/drop")
def drop_rtmp_publisher(
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
    return {"status": "dropped", "server_stream_id": server_stream_id}
