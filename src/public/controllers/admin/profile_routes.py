"""Transcode profile admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.transcode.service import TranscodeProfileService
from .dependencies import get_current_admin

router = APIRouter(prefix="/profiles", tags=["Admin Transcode Profiles"])


class ProfileCreate(BaseModel):
    profile_name: str
    profile_command: Optional[str] = None
    profile_type: str = "live"
    enabled: bool = True


class ProfileUpdate(BaseModel):
    profile_name: Optional[str] = None
    profile_command: Optional[str] = None
    profile_type: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("")
def list_profiles(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"profiles": TranscodeProfileService(db).get_all()}


@router.get("/presets")
def list_presets(
    admin: User = Depends(get_current_admin),
):
    return {"presets": TranscodeProfileService.__new__(TranscodeProfileService).get_presets()}


@router.get("/{profile_id}")
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = TranscodeProfileService(db).get_by_id(profile_id)
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.post("")
def create_profile(
    data: ProfileCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return TranscodeProfileService(db).create(data.model_dump(exclude_none=True))


@router.put("/{profile_id}")
def update_profile(
    profile_id: int,
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = TranscodeProfileService(db).update(profile_id, data.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Profile not found")
    return result


@router.delete("/{profile_id}")
def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not TranscodeProfileService(db).delete(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"status": "deleted"}


@router.post("/test/{profile_id}")
def test_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return TranscodeProfileService(db).test_profile(profile_id)
