from datetime import datetime, timezone
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from src.core.database import get_db
from src.domain.stream.service import StreamService
from src.domain.models import User
from src.streaming.engine import streaming_engine
from .dependencies import get_current_admin

router = APIRouter(prefix="/streams", tags=["Admin Streams"])


class StreamCreate(BaseModel):
    stream_display_name: str
    stream_source: Optional[str] = None
    stream_icon: Optional[str] = None
    epg_channel_id: Optional[str] = None
    category_id: Optional[int] = None
    stream_type: int = 1
    enabled: bool = True
    direct_source: bool = False
    notes: Optional[str] = None
    target_container: str = "ts"
    tv_archive: bool = False
    tv_archive_duration: int = 0
    custom_ffmpeg: Optional[str] = None
    read_native: bool = False
    stream_all: bool = False
    allow_record: bool = False
    order: int = 0
    custom_sid: Optional[str] = None
    tv_archive_server_id: Optional[int] = None


class StreamUpdate(BaseModel):
    stream_display_name: Optional[str] = None
    stream_source: Optional[str] = None
    stream_icon: Optional[str] = None
    epg_channel_id: Optional[str] = None
    category_id: Optional[int] = None
    stream_type: Optional[int] = None
    enabled: Optional[bool] = None
    direct_source: Optional[bool] = None
    notes: Optional[str] = None
    target_container: Optional[str] = None
    tv_archive: Optional[bool] = None
    tv_archive_duration: Optional[int] = None
    custom_ffmpeg: Optional[str] = None
    read_native: Optional[bool] = None
    stream_all: Optional[bool] = None
    allow_record: Optional[bool] = None
    order: Optional[int] = None
    custom_sid: Optional[str] = None
    tv_archive_server_id: Optional[int] = None


class StreamProbeRequest(BaseModel):
    url: Optional[str] = None


class BatchAction(BaseModel):
    ids: List[int]


@router.get("")
def list_streams(
    page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
    category_id: Optional[int] = None, stream_type: Optional[int] = None,
    enabled: Optional[bool] = None,
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin),
):
    svc = StreamService(db)
    result = svc.get_all(category_id=category_id, stream_type=stream_type, enabled=enabled, page=page, per_page=per_page)
    result["items"] = [_stream_to_dict(s) for s in result["items"]]
    return result


@router.get("/stats")
def stream_stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return StreamService(db).get_stats()


@router.get("/runtime")
def stream_runtime(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = StreamService(db)
    active = streaming_engine.get_active_streams()
    rows = {}
    for stream in svc.get_all(page=1, per_page=1000000)["items"]:
        info = active.get(stream.id)
        started_at = info.get("started_at") if info else (stream.stream_started_at.isoformat() if stream.stream_started_at else None)
        uptime_seconds = None
        if started_at:
            try:
                started = datetime.fromisoformat(started_at)
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                uptime_seconds = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
            except ValueError:
                uptime_seconds = None
        rows[stream.id] = {
            "running": bool(info and info.get("running")) or stream.stream_status == 1,
            "pid": info.get("pid") if info else stream.stream_pid,
            "started_at": started_at,
            "uptime_seconds": uptime_seconds,
        }
    return {"items": rows}


@router.get("/search")
def search_streams(q: str = Query(..., min_length=1), db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return [_stream_to_dict(s) for s in StreamService(db).search(q)]


@router.get("/{stream_id}")
def get_stream(stream_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    stream = StreamService(db).get_by_id(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return _stream_to_dict(stream)


def _stream_sources_or_400(svc: StreamService, stream_id: int) -> List[str]:
    sources = svc.get_sources(stream_id)
    if not sources:
        raise HTTPException(status_code=400, detail="No stream source configured")
    return sources


@router.post("/{stream_id}/start")
def start_stream_engine(
    stream_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin),
):
    svc = StreamService(db)
    stream = svc.get_by_id(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    sources = _stream_sources_or_400(svc, stream_id)
    pid = streaming_engine.start_stream(
        stream_id,
        sources[0],
        container=stream.target_container,
        custom_ffmpeg=stream.custom_ffmpeg,
        read_native=stream.read_native,
        server_id=stream.tv_archive_server_id,
    )
    if pid is None:
        raise HTTPException(status_code=500, detail="Failed to start streaming process")
    stream.stream_status = 1
    stream.stream_pid = pid
    stream.stream_started_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "started", "pid": pid, "stream_id": stream_id}


@router.post("/{stream_id}/stop")
def stop_stream_engine(
    stream_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin),
):
    stream = StreamService(db).get_by_id(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    stopped = streaming_engine.stop_stream(stream_id)
    stream.stream_status = 0
    stream.stream_pid = None
    stream.stream_started_at = None
    db.commit()
    return {"status": "stopped" if stopped else "not_running", "stream_id": stream_id}


@router.post("/{stream_id}/restart")
def restart_stream_engine(
    stream_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin),
):
    svc = StreamService(db)
    stream = svc.get_by_id(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    sources = _stream_sources_or_400(svc, stream_id)
    streaming_engine.stop_stream(stream_id)
    pid = streaming_engine.start_stream(
        stream_id,
        sources[0],
        container=stream.target_container,
        custom_ffmpeg=stream.custom_ffmpeg,
        read_native=stream.read_native,
        server_id=stream.tv_archive_server_id,
    )
    if pid is None:
        raise HTTPException(status_code=500, detail="Failed to restart streaming process")
    stream.stream_status = 1
    stream.stream_pid = pid
    stream.stream_started_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "restarted", "pid": pid, "stream_id": stream_id}


@router.get("/{stream_id}/status")
def stream_engine_status(
    stream_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin),
):
    stream = StreamService(db).get_by_id(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    info = streaming_engine.get_stream_info(stream_id)
    return {
        "stream_id": stream_id,
        "running": streaming_engine.is_active(stream_id),
        "engine": info,
    }


@router.post("/{stream_id}/probe")
def probe_stream_source(
    stream_id: int,
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin),
    data: Optional[StreamProbeRequest] = Body(None),
):
    svc = StreamService(db)
    stream = svc.get_by_id(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    payload = data if data is not None else StreamProbeRequest()
    url = (payload.url or "").strip()
    if not url:
        sources = _stream_sources_or_400(svc, stream_id)
        url = sources[0]
    result = streaming_engine.probe_stream(url)
    if result is None:
        raise HTTPException(status_code=502, detail="Probe failed or timed out")
    return {"url": url, "probe": result}


@router.post("")
def create_stream(data: StreamCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return _stream_to_dict(StreamService(db).create(data.model_dump(exclude_none=True)))


@router.put("/{stream_id}")
def update_stream(stream_id: int, data: StreamUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    stream = StreamService(db).update(stream_id, data.model_dump(exclude_none=True))
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return _stream_to_dict(stream)


@router.delete("/{stream_id}")
def delete_stream(stream_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    if not StreamService(db).delete(stream_id):
        raise HTTPException(status_code=404, detail="Stream not found")
    return {"status": "deleted"}


@router.post("/{stream_id}/toggle")
def toggle_stream(stream_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    stream = StreamService(db).toggle_status(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return _stream_to_dict(stream)


@router.post("/batch/enable")
def batch_enable(data: BatchAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return {"affected": StreamService(db).batch_toggle(data.ids, True)}


@router.post("/batch/disable")
def batch_disable(data: BatchAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return {"affected": StreamService(db).batch_toggle(data.ids, False)}


@router.post("/batch/delete")
def batch_delete_streams(data: BatchAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return {"affected": StreamService(db).batch_delete(data.ids)}


def _stream_to_dict(s) -> dict:
    return {
        "id": s.id, "stream_display_name": s.stream_display_name,
        "stream_source": s.stream_source, "stream_icon": s.stream_icon,
        "epg_channel_id": s.epg_channel_id, "category_id": s.category_id,
        "stream_type": s.stream_type, "enabled": s.enabled,
        "direct_source": s.direct_source, "target_container": s.target_container,
        "notes": s.notes, "added": str(s.added) if s.added else None,
        "tv_archive": s.tv_archive, "tv_archive_duration": s.tv_archive_duration,
        "order": s.order,
        "custom_ffmpeg": s.custom_ffmpeg,
        "read_native": s.read_native,
        "stream_all": s.stream_all,
        "allow_record": s.allow_record,
        "custom_sid": s.custom_sid,
        "probed_resolution": s.probed_resolution,
        "current_source": s.current_source,
        "stream_status": s.stream_status,
        "stream_pid": s.stream_pid,
        "stream_started_at": s.stream_started_at.isoformat() if s.stream_started_at else None,
        "tv_archive_server_id": s.tv_archive_server_id,
    }
