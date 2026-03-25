"""Access code management for admin panel authentication."""

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.util.encryption import generate_token
from src.domain.models import User
from src.domain.server.settings_service import SettingsService

from .dependencies import get_current_admin

router = APIRouter(prefix="/access-codes", tags=["Admin Access Codes"])


class AccessCodeCreate(BaseModel):
    name: str
    code: str = ""
    permissions: str = "full"


@router.get("")
def list_codes(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("access_codes", "[]")
    codes = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    return {"codes": codes}


@router.post("")
def create_code(data: AccessCodeCreate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("access_codes", "[]")
    codes = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    code = {
        "id": len(codes) + 1,
        "name": data.name,
        "code": data.code or generate_token(16),
        "permissions": data.permissions,
        "enabled": True,
    }
    codes.append(code)
    svc.set("access_codes", codes, "json")
    return code


@router.post("/generate")
def generate_code(admin: User = Depends(get_current_admin)):
    return {"code": generate_token(16)}


@router.delete("/{code_id}")
def delete_code(code_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("access_codes", "[]")
    codes = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    codes = [c for c in codes if c.get("id") != code_id]
    svc.set("access_codes", codes, "json")
    return {"status": "deleted"}
