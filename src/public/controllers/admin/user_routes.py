from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from src.core.database import get_db
from src.domain.user.service import UserService
from src.domain.models import User
from .dependencies import get_current_admin

router = APIRouter(prefix="/users", tags=["Admin Users"])


class UserCreate(BaseModel):
    username: str
    password: str
    max_connections: int = 1
    exp_date: Optional[datetime] = None
    is_trial: bool = False
    enabled: bool = True
    admin_notes: Optional[str] = None
    bouquet: Optional[str] = None
    allowed_output_ids: Optional[str] = None
    allowed_ips: Optional[str] = None
    allowed_user_agents: Optional[str] = None
    force_server_id: Optional[int] = None
    reseller_notes: Optional[str] = None
    is_restreamer: bool = False
    is_mag: bool = False
    is_stalker: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    max_connections: Optional[int] = None
    exp_date: Optional[datetime] = None
    is_trial: Optional[bool] = None
    enabled: Optional[bool] = None
    admin_notes: Optional[str] = None
    bouquet: Optional[str] = None
    allowed_output_ids: Optional[str] = None
    allowed_ips: Optional[str] = None
    allowed_user_agents: Optional[str] = None
    force_server_id: Optional[int] = None
    reseller_notes: Optional[str] = None
    is_restreamer: Optional[bool] = None
    is_mag: Optional[bool] = None
    is_stalker: Optional[bool] = None


class BatchAction(BaseModel):
    ids: List[int]


@router.get("")
def list_users(
    page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None, enabled: Optional[bool] = None,
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin),
):
    svc = UserService(db)
    result = svc.get_all(page=page, per_page=per_page, search=search, enabled=enabled)
    result["items"] = [_user_to_dict(u) for u in result["items"]]
    return result


@router.get("/stats")
def user_stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return UserService(db).get_stats()


@router.get("/online")
def online_users(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return UserService(db).get_online_users()


@router.get("/generate")
def generate_credentials(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return UserService(db).generate_credentials()


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = UserService(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(user)


@router.post("")
def create_user(data: UserCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = UserService(db)
    existing = svc.get_by_username(data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    return _user_to_dict(svc.create(data.model_dump(exclude_none=True)))


@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = UserService(db).update(user_id, data.model_dump(exclude_none=True))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(user)


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    if not UserService(db).delete(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "deleted"}


@router.post("/{user_id}/toggle")
def toggle_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    user = UserService(db).toggle_status(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_dict(user)


@router.post("/batch/enable")
def batch_enable(data: BatchAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return {"affected": UserService(db).batch_toggle(data.ids, True)}


@router.post("/batch/disable")
def batch_disable(data: BatchAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return {"affected": UserService(db).batch_toggle(data.ids, False)}


@router.post("/batch/delete")
def batch_delete_users(data: BatchAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return {"affected": UserService(db).batch_delete(data.ids)}


def _user_to_dict(u) -> dict:
    return {
        "id": u.id, "username": u.username, "max_connections": u.max_connections,
        "exp_date": str(u.exp_date) if u.exp_date else None,
        "is_trial": u.is_trial, "enabled": u.enabled,
        "admin_notes": u.admin_notes, "bouquet": u.bouquet,
        "allowed_ips": u.allowed_ips,
        "allowed_user_agents": u.allowed_user_agents,
        "allowed_output_ids": u.allowed_output_ids,
        "force_server_id": u.force_server_id,
        "reseller_notes": u.reseller_notes,
        "is_admin": u.is_admin,
        "is_restreamer": u.is_restreamer, "is_mag": u.is_mag,
        "is_stalker": u.is_stalker, "created_at": str(u.created_at) if u.created_at else None,
    }
