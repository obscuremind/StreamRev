"""Ministra admin API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.public.controllers.admin.dependencies import get_current_admin
from src.domain.models import User
from src.modules.ministra.service import MinistraService

router = APIRouter(prefix="/api/admin/ministra", tags=["Ministra/Stalker"])

@router.get("/config")
def get_config(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return MinistraService(db).get_portal_config()

@router.post("/config")
def update_config(payload: dict, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    cfg = MinistraService(db).set_portal_config(payload)
    return {"status": "saved", "config": cfg}

@router.post("/sync")
def trigger_sync(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = MinistraService(db).sync_users()
    return {"status": "completed", **result}

@router.get("/profiles")
def list_profiles(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    p = MinistraService(db).get_stb_profiles()
    return {"profiles": p, "total": len(p)}

@router.get("/status")
def module_status(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return MinistraService(db).get_status()
