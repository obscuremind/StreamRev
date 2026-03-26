from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional

from src.core.database import get_db
from src.domain.epg.service import EpgService
from src.domain.models import User
from .dependencies import get_current_admin

router = APIRouter(prefix="/epg", tags=["Admin EPG"])


class EpgProgramCreate(BaseModel):
    epg_id: Optional[str] = None
    title: str = ""
    lang: Optional[str] = None
    start: datetime
    end: datetime
    description: Optional[str] = None
    channel_id: Optional[int] = None


class EpgProgramUpdate(BaseModel):
    epg_id: Optional[str] = None
    title: Optional[str] = None
    lang: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    description: Optional[str] = None
    channel_id: Optional[int] = None


class XmltvImportBody(BaseModel):
    xml_content: str


@router.get("/programs")
def list_epg_programs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    epg_id: Optional[str] = None,
    channel_id: Optional[int] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = EpgService(db)
    result = svc.list_programs(
        epg_id=epg_id, channel_id=channel_id, page=page, per_page=per_page
    )
    result["items"] = [_epg_to_dict(p) for p in result["items"]]
    return result


@router.get("/programs/{program_id}")
def get_epg_program(
    program_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    p = EpgService(db).get_program_by_id(program_id)
    if not p:
        raise HTTPException(status_code=404, detail="EPG program not found")
    return _epg_to_dict(p)


@router.post("/programs")
def create_epg_program(
    data: EpgProgramCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return _epg_to_dict(EpgService(db).create_program(data.model_dump(exclude_none=True)))


@router.put("/programs/{program_id}")
def update_epg_program(
    program_id: int,
    data: EpgProgramUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    p = EpgService(db).update_program(program_id, data.model_dump(exclude_none=True))
    if not p:
        raise HTTPException(status_code=404, detail="EPG program not found")
    return _epg_to_dict(p)


@router.delete("/programs/{program_id}")
def delete_epg_program(
    program_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not EpgService(db).delete_program(program_id):
        raise HTTPException(status_code=404, detail="EPG program not found")
    return {"status": "deleted"}


@router.get("/stats")
def epg_stats(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return EpgService(db).get_stats()


@router.post("/import/xmltv")
def import_xmltv(
    body: XmltvImportBody,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = EpgService(db).import_xmltv(body.xml_content)
    return {"imported": count}


@router.post("/maintenance/clear-old")
def clear_old_epg(
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"deleted": EpgService(db).clear_old(days)}


@router.post("/maintenance/clear-all")
def clear_all_epg(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return {"deleted": EpgService(db).clear_all()}


def _epg_to_dict(p) -> dict[str, Any]:
    return {
        "id": p.id,
        "epg_id": p.epg_id,
        "title": p.title,
        "lang": p.lang,
        "start": p.start.isoformat() if p.start else None,
        "end": p.end.isoformat() if p.end else None,
        "description": p.description,
        "channel_id": p.channel_id,
    }
