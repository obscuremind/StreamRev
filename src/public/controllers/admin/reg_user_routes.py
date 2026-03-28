"""Registration management admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.registration.service import RegistrationService
from .dependencies import get_current_admin

router = APIRouter(prefix="/registrations", tags=["Admin Registrations"])


class BatchIdsRequest(BaseModel):
    ids: List[int]


@router.get("")
def list_registrations(
    page: int = 1,
    per_page: int = 50,
    status: Optional[int] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return RegistrationService(db).get_all(page=page, per_page=per_page, status=status)


@router.get("/{reg_id}")
def get_registration(
    reg_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = RegistrationService(db).get_by_id(reg_id)
    if not result:
        raise HTTPException(status_code=404, detail="Registration not found")
    return result


@router.post("/approve/{reg_id}")
def approve_registration(
    reg_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = RegistrationService(db).approve(reg_id)
    if not result:
        raise HTTPException(status_code=404, detail="Registration not found")
    return result


@router.post("/reject/{reg_id}")
def reject_registration(
    reg_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = RegistrationService(db).reject(reg_id)
    if not result:
        raise HTTPException(status_code=404, detail="Registration not found")
    return result


@router.post("/batch-approve")
def batch_approve(
    data: BatchIdsRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = RegistrationService(db).batch_approve(data.ids)
    return {"status": "approved", "count": count}


@router.post("/batch-reject")
def batch_reject(
    data: BatchIdsRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = RegistrationService(db).batch_reject(data.ids)
    return {"status": "rejected", "count": count}


@router.delete("/{reg_id}")
def delete_registration(
    reg_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not RegistrationService(db).delete(reg_id):
        raise HTTPException(status_code=404, detail="Registration not found")
    return {"status": "deleted"}
