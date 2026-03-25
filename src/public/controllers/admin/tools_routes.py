"""Admin tools: channel ordering, process monitor, live connections, RTMP, ISP/ASN, profiles, user groups, credit logs, edit profile, radio management, created channels."""

import json
from typing import Any, Dict, List, Optional

import psutil
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.domain.models import User, Stream, StreamLog
from src.domain.stream.radio_service import RadioService
from src.domain.stream.channel_service import ChannelService
from src.domain.stream.connection_tracker import ConnectionTracker
from src.domain.stream.playlist_generator import ProfileService
from src.domain.server.settings_service import SettingsService
from src.streaming.engine import streaming_engine

from .dependencies import get_current_admin

router = APIRouter(tags=["Admin Tools"])


# --- Channel Ordering ---
class OrderUpdate(BaseModel):
    items: List[Dict[str, int]]


@router.put("/channel-order")
def update_channel_order(
    data: OrderUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    count = 0
    for item in data.items:
        sid = item.get("id")
        order = item.get("order", 0)
        if sid:
            db.query(Stream).filter(Stream.id == sid).update({"order": order})
            count += 1
    db.commit()
    return {"updated": count}


# --- Live Connections ---
@router.get("/live-connections")
def live_connections(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    tracker = ConnectionTracker(db)
    return {"connections": tracker.get_live_connections(), "total": tracker.get_connection_count()}


# --- Process Monitor ---
@router.get("/process-monitor")
def process_monitor(admin: User = Depends(get_current_admin)):
    processes = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status", "create_time"]):
        try:
            info = p.info
            if any(
                k in (info["name"] or "").lower()
                for k in ("ffmpeg", "uvicorn", "nginx", "redis", "mysql", "mariadb", "python")
            ):
                processes.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu": info["cpu_percent"],
                        "memory": info["memory_percent"],
                        "status": info["status"],
                    }
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    engine_stats = streaming_engine.get_stats()
    return {"processes": processes, "streaming": engine_stats}


# --- Transcoding Profiles ---
@router.get("/profiles")
def list_profiles(admin: User = Depends(get_current_admin)):
    return {"profiles": ProfileService.get_all_profiles()}


@router.get("/profiles/{name}")
def get_profile(name: str, admin: User = Depends(get_current_admin)):
    profile = ProfileService.get_profile(name)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"name": name, "config": profile, "ffmpeg_args": ProfileService.build_ffmpeg_args(name)}


# --- RTMP Management ---
@router.get("/rtmp/status")
def rtmp_status(admin: User = Depends(get_current_admin)):
    return {"active_publishers": 0, "active_players": 0, "status": "monitoring"}


@router.get("/rtmp/ips")
def rtmp_allowed_ips(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("rtmp_allowed_ips", "[]")
    ips = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    return {"ips": ips}


# --- ISP/ASN Blocking ---
@router.get("/blocked-isps")
def list_blocked_isps(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("blocked_isps", "[]")
    isps = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    return {"isps": isps}


class ISPAction(BaseModel):
    isp: str


@router.post("/blocked-isps/add")
def block_isp(data: ISPAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("blocked_isps", "[]")
    isps = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    if data.isp not in isps:
        isps.append(data.isp)
        svc.set("blocked_isps", isps, "json")
    return {"status": "blocked"}


@router.post("/blocked-isps/remove")
def unblock_isp(data: ISPAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("blocked_isps", "[]")
    isps = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    isps = [i for i in isps if i != data.isp]
    svc.set("blocked_isps", isps, "json")
    return {"status": "unblocked"}


# --- User Groups ---
@router.get("/user-groups")
def list_user_groups(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = SettingsService(db)
    raw = svc.get("user_groups", "[]")
    return {"groups": json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []}


class GroupData(BaseModel):
    name: str
    bouquets: Optional[str] = None
    max_connections: int = 1


@router.post("/user-groups")
def create_user_group(
    data: GroupData, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    svc = SettingsService(db)
    raw = svc.get("user_groups", "[]")
    groups = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    group = {
        "id": len(groups) + 1,
        "name": data.name,
        "bouquets": data.bouquets,
        "max_connections": data.max_connections,
    }
    groups.append(group)
    svc.set("user_groups", groups, "json")
    return group


@router.delete("/user-groups/{group_id}")
def delete_user_group(
    group_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    svc = SettingsService(db)
    raw = svc.get("user_groups", "[]")
    groups = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    groups = [g for g in groups if g.get("id") != group_id]
    svc.set("user_groups", groups, "json")
    return {"status": "deleted"}


# --- Credit Logs ---
@router.get("/credit-logs")
def credit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SettingsService(db)
    raw = svc.get("credit_logs", "[]")
    logs = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    total = len(logs)
    start = (page - 1) * per_page
    return {"items": logs[start : start + per_page], "total": total, "page": page, "per_page": per_page}


# --- Stream Errors/Review ---
@router.get("/stream-errors")
def stream_errors(
    stream_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = db.query(StreamLog).filter(StreamLog.log_type == "error")
    if stream_id:
        query = query.filter(StreamLog.stream_id == stream_id)
    total = query.count()
    items = query.order_by(StreamLog.date.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [{"id": l.id, "stream_id": l.stream_id, "date": str(l.date), "info": l.info} for l in items],
        "total": total,
        "page": page,
    }


def _stream_brief(s: Stream) -> Dict[str, Any]:
    return {
        "id": s.id,
        "stream_display_name": s.stream_display_name,
        "stream_type": s.stream_type,
        "category_id": s.category_id,
        "stream_icon": s.stream_icon,
        "enabled": s.enabled,
    }


# --- Radio Management ---
@router.get("/radios")
def list_radios(
    page: int = Query(1, ge=1),
    per_page: int = Query(50),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = RadioService(db).get_all_radios(page=page, per_page=per_page)
    result["items"] = [_stream_brief(s) for s in result["items"]]
    return result


@router.get("/radios/categories")
def radio_categories(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    cats = RadioService(db).get_radio_categories()
    return [{"id": c.id, "category_name": c.category_name} for c in cats]


# --- Created Channels ---
@router.get("/created-channels")
def list_created_channels(
    page: int = Query(1, ge=1),
    per_page: int = Query(50),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = ChannelService(db).get_created_channels(page=page, per_page=per_page)
    result["items"] = [_stream_brief(s) for s in result["items"]]
    return result


# --- Edit Admin Profile ---
class ProfileUpdate(BaseModel):
    password: Optional[str] = None
    admin_notes: Optional[str] = None


@router.get("/profile")
def get_admin_profile(admin: User = Depends(get_current_admin)):
    return {
        "id": admin.id,
        "username": admin.username,
        "admin_notes": admin.admin_notes,
        "created_at": str(admin.created_at) if admin.created_at else None,
    }


@router.put("/profile")
def update_admin_profile(
    data: ProfileUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    from src.domain.user.service import UserService

    svc = UserService(db)
    updates = data.model_dump(exclude_none=True)
    if updates:
        svc.update(admin.id, updates)
    return {"status": "updated"}
