"""Admin routes for MAG and Enigma2 device management."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.domain.models import User
from src.domain.device.mag_service import MagService
from src.domain.device.enigma_service import EnigmaService

from .dependencies import get_current_admin

router = APIRouter(tags=["Admin Devices"])


class DeviceCreate(BaseModel):
    username: str
    password: str
    max_connections: int = 1
    exp_date: Optional[datetime] = None
    enabled: bool = True
    admin_notes: Optional[str] = None
    bouquet: Optional[str] = None
    allowed_ips: Optional[str] = None


class DeviceUpdate(BaseModel):
    password: Optional[str] = None
    max_connections: Optional[int] = None
    exp_date: Optional[datetime] = None
    enabled: Optional[bool] = None
    admin_notes: Optional[str] = None
    bouquet: Optional[str] = None
    allowed_ips: Optional[str] = None


def _user_to_dict(u) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "max_connections": u.max_connections,
        "exp_date": str(u.exp_date) if u.exp_date else None,
        "enabled": u.enabled,
        "admin_notes": u.admin_notes,
        "bouquet": u.bouquet,
        "allowed_ips": u.allowed_ips,
        "is_mag": u.is_mag,
        "is_stalker": u.is_stalker,
        "created_at": str(u.created_at) if u.created_at else None,
    }


# --- MAG Devices ---
@router.get("/mags")
def list_mags(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = MagService(db).get_all_mags(page=page, per_page=per_page, search=search)
    result["items"] = [_user_to_dict(u) for u in result["items"]]
    return result


@router.get("/mags/{user_id}")
def get_mag(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    mag = MagService(db).get_mag_by_id(user_id)
    if not mag:
        raise HTTPException(status_code=404, detail="MAG device not found")
    return _user_to_dict(mag)


@router.post("/mags")
def create_mag(data: DeviceCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return _user_to_dict(MagService(db).create_mag(data.model_dump(exclude_none=True)))


@router.put("/mags/{user_id}")
def update_mag(
    user_id: int,
    data: DeviceUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    mag = MagService(db).update_mag(user_id, data.model_dump(exclude_none=True))
    if not mag:
        raise HTTPException(status_code=404, detail="MAG device not found")
    return _user_to_dict(mag)


@router.delete("/mags/{user_id}")
def delete_mag(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    if not MagService(db).delete_mag(user_id):
        raise HTTPException(status_code=404, detail="MAG device not found")
    return {"status": "deleted"}


# --- Enigma2 Devices ---
@router.get("/enigmas")
def list_enigmas(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = EnigmaService(db).get_all_enigmas(page=page, per_page=per_page, search=search)
    result["items"] = [_user_to_dict(u) for u in result["items"]]
    return result


@router.get("/enigmas/{user_id}")
def get_enigma(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    enigma = EnigmaService(db).get_enigma_by_id(user_id)
    if not enigma:
        raise HTTPException(status_code=404, detail="Enigma2 device not found")
    return _user_to_dict(enigma)


@router.post("/enigmas")
def create_enigma(data: DeviceCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return _user_to_dict(EnigmaService(db).create_enigma(data.model_dump(exclude_none=True)))


@router.put("/enigmas/{user_id}")
def update_enigma(
    user_id: int,
    data: DeviceUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    enigma = EnigmaService(db).update_enigma(user_id, data.model_dump(exclude_none=True))
    if not enigma:
        raise HTTPException(status_code=404, detail="Enigma2 device not found")
    return _user_to_dict(enigma)


@router.delete("/enigmas/{user_id}")
def delete_enigma(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    if not EnigmaService(db).delete_enigma(user_id):
        raise HTTPException(status_code=404, detail="Enigma2 device not found")
    return {"status": "deleted"}
