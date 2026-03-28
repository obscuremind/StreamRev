"""Audit log admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.audit.service import AuditService
from .dependencies import get_current_admin

router = APIRouter(prefix="/audit", tags=["Admin Audit"])


class CleanupRequest(BaseModel):
    days: int = 90


@router.get("")
def list_audit(
    page: int = 1,
    per_page: int = 50,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return AuditService(db).get_all(page=page, per_page=per_page, action=action)


@router.get("/{audit_id}")
def get_audit_entry(
    audit_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = AuditService(db).get_by_id(audit_id)
    if not result:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return result


@router.get("/admin/{admin_id}")
def audit_by_admin(
    admin_id: int,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return AuditService(db).get_by_admin(admin_id, page=page, per_page=per_page)


@router.get("/entity/{entity_type}/{entity_id}")
def audit_by_entity(
    entity_type: str,
    entity_id: int,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return AuditService(db).get_by_entity(entity_type, entity_id, page=page, per_page=per_page)


@router.delete("/cleanup")
def cleanup_audit(
    data: CleanupRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = AuditService(db).cleanup(days=data.days)
    return {"status": "cleaned", "count": count}
