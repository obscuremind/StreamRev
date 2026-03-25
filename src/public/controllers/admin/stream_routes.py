from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from src.core.database import get_db
from src.domain.stream.service import StreamService
from src.domain.models import User
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


class StreamUpdate(BaseModel):
    stream_display_name: Optional[str] = None
    stream_source: Optional[str] = None
    stream_icon: Optional[str] = None
    epg_channel_id: Optional[str] = None
    category_id: Optional[int] = None
    enabled: Optional[bool] = None
    direct_source: Optional[bool] = None
    notes: Optional[str] = None
    target_container: Optional[str] = None
    tv_archive: Optional[bool] = None
    tv_archive_duration: Optional[int] = None


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


@router.get("/search")
def search_streams(q: str = Query(..., min_length=1), db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return [_stream_to_dict(s) for s in StreamService(db).search(q)]


@router.get("/{stream_id}")
def get_stream(stream_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    stream = StreamService(db).get_by_id(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return _stream_to_dict(stream)


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
    }
