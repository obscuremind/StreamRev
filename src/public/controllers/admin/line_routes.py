from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, List, Optional, Union

from src.core.database import get_db
from src.domain.line.service import LineService, PackageService
from src.domain.models import User
from .dependencies import get_current_admin

router = APIRouter(prefix="/lines", tags=["Admin Lines"])


# --- Packages (declare before /{line_id} patterns) ---


class PackageCreate(BaseModel):
    package_name: str = ""
    is_trial: bool = False
    is_official: bool = True
    trial_credits: int = 0
    official_credits: int = 0
    trial_duration: int = 0
    official_duration: int = 0
    max_connections: int = 1
    allowed_bouquets: Union[str, List[Any]] = Field(default_factory=list)
    allowed_output_types: Union[str, List[Any]] = Field(default_factory=list)
    can_general_edit: bool = False
    activity_type: Optional[str] = None
    only_mag: bool = False
    only_enigma: bool = False
    force_server_id: Optional[int] = None
    max_sub_resellers: int = 0
    only_stalker: bool = False


class PackageUpdate(BaseModel):
    package_name: Optional[str] = None
    is_trial: Optional[bool] = None
    is_official: Optional[bool] = None
    trial_credits: Optional[int] = None
    official_credits: Optional[int] = None
    trial_duration: Optional[int] = None
    official_duration: Optional[int] = None
    max_connections: Optional[int] = None
    allowed_bouquets: Optional[Union[str, List[Any]]] = None
    allowed_output_types: Optional[Union[str, List[Any]]] = None
    can_general_edit: Optional[bool] = None
    activity_type: Optional[str] = None
    only_mag: Optional[bool] = None
    only_enigma: Optional[bool] = None
    force_server_id: Optional[int] = None
    max_sub_resellers: Optional[int] = None
    only_stalker: Optional[bool] = None


@router.get("/packages")
def list_packages(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return [_package_to_dict(p) for p in PackageService(db).get_all()]


@router.get("/packages/{package_id}")
def get_package(
    package_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    p = PackageService(db).get_by_id(package_id)
    if not p:
        raise HTTPException(status_code=404, detail="Package not found")
    return _package_to_dict(p)


@router.post("/packages")
def create_package(
    data: PackageCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return _package_to_dict(PackageService(db).create(data.model_dump(exclude_none=True)))


@router.put("/packages/{package_id}")
def update_package(
    package_id: int,
    data: PackageUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    p = PackageService(db).update(package_id, data.model_dump(exclude_none=True))
    if not p:
        raise HTTPException(status_code=404, detail="Package not found")
    return _package_to_dict(p)


@router.delete("/packages/{package_id}")
def delete_package(
    package_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not PackageService(db).delete(package_id):
        raise HTTPException(status_code=404, detail="Package not found")
    return {"status": "deleted"}


def _package_to_dict(p) -> dict[str, Any]:
    return {
        "id": p.id,
        "package_name": p.package_name,
        "is_trial": p.is_trial,
        "is_official": p.is_official,
        "trial_credits": p.trial_credits,
        "official_credits": p.official_credits,
        "trial_duration": p.trial_duration,
        "official_duration": p.official_duration,
        "max_connections": p.max_connections,
        "allowed_bouquets": p.allowed_bouquets,
        "allowed_output_types": p.allowed_output_types,
        "can_general_edit": p.can_general_edit,
        "activity_type": p.activity_type,
        "only_mag": p.only_mag,
        "only_enigma": p.only_enigma,
        "force_server_id": p.force_server_id,
        "max_sub_resellers": p.max_sub_resellers,
        "only_stalker": p.only_stalker,
    }


# --- Active lines ---


class LineCreate(BaseModel):
    user_id: int
    server_id: int
    stream_id: int
    container: str = "ts"
    pid: Optional[int] = None
    user_agent: Optional[str] = None
    user_ip: Optional[str] = None
    geoip_country_code: Optional[str] = None
    bitrate: Optional[int] = None
    external_device: Optional[str] = None


class LineUpdate(BaseModel):
    server_id: Optional[int] = None
    stream_id: Optional[int] = None
    container: Optional[str] = None
    pid: Optional[int] = None
    user_agent: Optional[str] = None
    user_ip: Optional[str] = None
    geoip_country_code: Optional[str] = None
    bitrate: Optional[int] = None
    external_device: Optional[str] = None


@router.get("")
def list_active_lines(
    user_id: Optional[int] = None,
    stream_id: Optional[int] = None,
    server_id: Optional[int] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    lines = LineService(db).get_active_lines(
        user_id=user_id, stream_id=stream_id, server_id=server_id
    )
    return [_line_to_dict(line) for line in lines]


@router.get("/stats/online-count")
def online_connection_count(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return {"online_connections": LineService(db).get_online_count()}


@router.get("/{line_id}")
def get_line(
    line_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    line = LineService(db).get_by_id(line_id)
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")
    return _line_to_dict(line)


@router.post("")
def create_line(
    data: LineCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return _line_to_dict(LineService(db).create_line(data.model_dump(exclude_none=True)))


@router.put("/{line_id}")
def update_line(
    line_id: int,
    data: LineUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    line = LineService(db).update_line(line_id, data.model_dump(exclude_none=True))
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")
    return _line_to_dict(line)


@router.delete("/{line_id}")
def delete_line(
    line_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not LineService(db).remove_line(line_id):
        raise HTTPException(status_code=404, detail="Line not found")
    return {"status": "deleted"}


@router.post("/kick/user/{user_id}")
def kick_user_lines(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"removed": LineService(db).remove_user_lines(user_id)}


class UserActivityCreate(BaseModel):
    user_id: int
    stream_id: int
    server_id: int
    user_agent: Optional[str] = None
    user_ip: Optional[str] = None
    container: str = "ts"
    date_start: Optional[datetime] = None
    date_stop: Optional[datetime] = None
    geoip_country_code: Optional[str] = None


@router.post("/activity/log")
def log_user_activity(
    data: UserActivityCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    payload = data.model_dump(exclude_none=True)
    act = LineService(db).log_activity(payload)
    return {
        "id": act.id,
        "user_id": act.user_id,
        "stream_id": act.stream_id,
        "server_id": act.server_id,
        "date_start": str(act.date_start) if act.date_start else None,
        "date_stop": str(act.date_stop) if act.date_stop else None,
    }


def _line_to_dict(line) -> dict[str, Any]:
    return {
        "id": line.id,
        "user_id": line.user_id,
        "server_id": line.server_id,
        "stream_id": line.stream_id,
        "container": line.container,
        "pid": line.pid,
        "date": str(line.date) if line.date else None,
        "user_agent": line.user_agent,
        "user_ip": line.user_ip,
        "geoip_country_code": line.geoip_country_code,
        "bitrate": line.bitrate,
        "external_device": line.external_device,
    }
