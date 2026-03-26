from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, Optional

from src.core.database import get_db
from src.domain.line.service import ResellerService
from src.domain.models import User
from .dependencies import get_current_admin

router = APIRouter(prefix="/resellers", tags=["Admin Resellers"])


class ResellerCreate(BaseModel):
    username: str
    password: str
    owner_id: Optional[int] = None
    credits: int = 0
    notes: Optional[str] = None
    status: int = 1
    allowed_ips: Optional[str] = None
    max_credits: Optional[int] = None
    allowed_packages: Optional[str] = None


class ResellerUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    owner_id: Optional[int] = None
    credits: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[int] = None
    allowed_ips: Optional[str] = None
    max_credits: Optional[int] = None
    allowed_packages: Optional[str] = None


class CreditsAmount(BaseModel):
    amount: int


class CreditsSet(BaseModel):
    credits: int


@router.get("")
def list_resellers(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = ResellerService(db).get_all(page=page, per_page=per_page)
    result["items"] = [_reseller_to_dict(r) for r in result["items"]]
    return result


@router.get("/stats")
def reseller_stats(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return ResellerService(db).get_stats()


@router.get("/{reseller_id}")
def get_reseller(
    reseller_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    r = ResellerService(db).get_by_id(reseller_id)
    if not r:
        raise HTTPException(status_code=404, detail="Reseller not found")
    return _reseller_to_dict(r)


@router.post("")
def create_reseller(
    data: ResellerCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = ResellerService(db)
    if svc.get_by_username(data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    return _reseller_to_dict(svc.create(data.model_dump(exclude_none=True)))


@router.put("/{reseller_id}")
def update_reseller(
    reseller_id: int,
    data: ResellerUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    r = ResellerService(db).update(reseller_id, data.model_dump(exclude_none=True))
    if not r:
        raise HTTPException(status_code=404, detail="Reseller not found")
    return _reseller_to_dict(r)


@router.delete("/{reseller_id}")
def delete_reseller(
    reseller_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not ResellerService(db).delete(reseller_id):
        raise HTTPException(status_code=404, detail="Reseller not found")
    return {"status": "deleted"}


@router.post("/{reseller_id}/credits/add")
def add_reseller_credits(
    reseller_id: int,
    body: CreditsAmount,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    r = ResellerService(db).add_credits(reseller_id, body.amount)
    if not r:
        raise HTTPException(
            status_code=400, detail="Could not add credits (not found or over max)"
        )
    return _reseller_to_dict(r)


@router.post("/{reseller_id}/credits/use")
def use_reseller_credits(
    reseller_id: int,
    body: CreditsAmount,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    ok = ResellerService(db).use_credits(reseller_id, body.amount)
    if not ok:
        raise HTTPException(status_code=400, detail="Insufficient credits or not found")
    return {"status": "ok"}


@router.post("/{reseller_id}/credits/set")
def set_reseller_credits(
    reseller_id: int,
    body: CreditsSet,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    r = ResellerService(db).set_credits(reseller_id, body.credits)
    if not r:
        raise HTTPException(
            status_code=400, detail="Could not set credits (not found or invalid)"
        )
    return _reseller_to_dict(r)


def _reseller_to_dict(r) -> dict[str, Any]:
    return {
        "id": r.id,
        "username": r.username,
        "owner_id": r.owner_id,
        "credits": r.credits,
        "notes": r.notes,
        "status": r.status,
        "allowed_ips": r.allowed_ips,
        "max_credits": r.max_credits,
        "allowed_packages": r.allowed_packages,
    }
