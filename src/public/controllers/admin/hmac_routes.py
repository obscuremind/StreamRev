"""HMAC key management admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.hmac.service import HmacKeyService
from .dependencies import get_current_admin

router = APIRouter(prefix="/hmac", tags=["Admin HMAC"])


class HmacCreate(BaseModel):
    key: Optional[str] = None
    notes: Optional[str] = None
    enabled: bool = True
    allowed_ips: Optional[str] = None


class HmacUpdate(BaseModel):
    notes: Optional[str] = None
    enabled: Optional[bool] = None
    allowed_ips: Optional[str] = None


class GenerateRequest(BaseModel):
    key_id: int
    message: str


@router.get("")
def list_hmac_keys(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"keys": HmacKeyService(db).get_all()}


@router.post("/create")
def create_hmac_key(
    data: HmacCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return HmacKeyService(db).create(data.model_dump(exclude_none=True))


@router.post("/generate")
def generate_signature(
    data: GenerateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = HmacKeyService(db).generate_signature(data.key_id, data.message)
    if not result:
        raise HTTPException(status_code=404, detail="HMAC key not found or disabled")
    return result


@router.put("/{key_id}")
def update_hmac_key(
    key_id: int,
    data: HmacUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = HmacKeyService(db).update(key_id, data.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="HMAC key not found")
    return result


@router.delete("/{key_id}")
def delete_hmac_key(
    key_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not HmacKeyService(db).delete(key_id):
        raise HTTPException(status_code=404, detail="HMAC key not found")
    return {"status": "deleted"}


@router.post("/{key_id}/toggle")
def toggle_hmac_key(
    key_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = HmacKeyService(db).toggle(key_id)
    if not result:
        raise HTTPException(status_code=404, detail="HMAC key not found")
    return result
