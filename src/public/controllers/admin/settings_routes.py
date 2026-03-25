from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.server.settings_service import SettingsService
from .dependencies import get_current_admin

router = APIRouter(prefix="/settings", tags=["Admin Settings"])


class SettingCreate(BaseModel):
    key: str
    value: Any = None
    value_type: str = "string"


class SettingUpdate(BaseModel):
    key: Optional[str] = None
    value: Optional[Any] = None
    value_type: Optional[str] = None


def _setting_row_to_dict(svc: SettingsService, row) -> dict[str, Any]:
    return {
        "id": row.id,
        "key": row.key,
        "value": SettingsService._cast_value(row.value or "", row.value_type),
        "value_type": row.value_type,
    }


@router.get("/values")
def get_all_setting_values(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return SettingsService(db).get_all()


@router.get("")
def list_setting_rows(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    svc = SettingsService(db)
    return [_setting_row_to_dict(svc, r) for r in svc.list_rows()]


@router.get("/{setting_id}")
def get_setting_row(
    setting_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SettingsService(db)
    row = svc.get_row_by_id(setting_id)
    if not row:
        raise HTTPException(status_code=404, detail="Setting not found")
    return _setting_row_to_dict(svc, row)


@router.post("")
def create_setting_row(
    data: SettingCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SettingsService(db)
    row = svc.create_row(data.key, data.value, data.value_type)
    return _setting_row_to_dict(svc, row)


@router.put("/{setting_id}")
def update_setting_row(
    setting_id: int,
    data: SettingUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SettingsService(db)
    row = svc.update_row(setting_id, data.model_dump(exclude_none=True))
    if not row:
        raise HTTPException(status_code=404, detail="Setting not found")
    return _setting_row_to_dict(svc, row)


@router.delete("/{setting_id}")
def delete_setting_row(
    setting_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SettingsService(db)
    if not svc.delete_row_by_id(setting_id):
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"status": "deleted"}


@router.delete("/by-key/{key:path}")
def delete_setting_by_key(
    key: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not SettingsService(db).delete(key):
        raise HTTPException(status_code=404, detail="Setting key not found")
    return {"status": "deleted"}
