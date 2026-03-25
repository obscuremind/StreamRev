import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.auth import create_access_token, decode_access_token
from src.domain.device.enigma_service import EnigmaService
from src.domain.device.mag_service import MagService
from src.domain.epg.service import EpgService
from src.domain.line.service import PackageService, ResellerService
from src.domain.models import (
    Bouquet,
    EpgData,
    Line,
    Movie,
    Package,
    Reseller,
    SeriesEpisode,
    Stream,
    User,
    UserActivity,
)
from src.domain.server.settings_service import SettingsService
from src.domain.stream.channel_service import ChannelService
from src.domain.stream.connection_tracker import ConnectionTracker
from src.domain.stream.radio_service import RadioService
from src.domain.user.service import UserService
router = APIRouter(tags=["Reseller API"])
security = HTTPBearer()


def get_current_reseller(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Reseller:
    payload = decode_access_token(credentials.credentials)
    if not payload or payload.get("role") != "reseller":
        raise HTTPException(status_code=401, detail="Invalid token")
    reseller = db.query(Reseller).filter(Reseller.id == int(payload["sub"])).first()
    if not reseller or reseller.status != 1:
        raise HTTPException(status_code=403, detail="Reseller access denied")
    return reseller


def _reseller_ticket_key(reseller_id: int) -> str:
    return f"reseller_tickets_{reseller_id}"


def _parse_package_ids(reseller: Reseller) -> Optional[List[int]]:
    raw = (reseller.allowed_packages or "").strip()
    if not raw:
        return None
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def _reseller_content_scope(db: Session, reseller: Reseller) -> Optional[Dict[str, Set[int]]]:
    pkg_ids = _parse_package_ids(reseller)
    if pkg_ids is None:
        return None
    if not pkg_ids:
        return {
            "stream_ids": set(),
            "movie_ids": set(),
            "radio_stream_ids": set(),
            "series_ids": set(),
        }
    stream_ids: Set[int] = set()
    movie_ids: Set[int] = set()
    radio_stream_ids: Set[int] = set()
    series_ids: Set[int] = set()
    for pid in pkg_ids:
        pkg = db.query(Package).filter(Package.id == pid).first()
        if not pkg:
            continue
        try:
            bq_ids = json.loads(pkg.allowed_bouquets or "[]")
        except json.JSONDecodeError:
            continue
        if not isinstance(bq_ids, list):
            continue
        for bid in bq_ids:
            try:
                bint = int(bid)
            except (TypeError, ValueError):
                continue
            b = db.query(Bouquet).filter(Bouquet.id == bint).first()
            if not b:
                continue
            for target, attr in (
                (stream_ids, "bouquet_channels"),
                (movie_ids, "bouquet_movies"),
                (radio_stream_ids, "bouquet_radios"),
                (series_ids, "bouquet_series"),
            ):
                try:
                    arr = json.loads(getattr(b, attr) or "[]")
                except json.JSONDecodeError:
                    continue
                if not isinstance(arr, list):
                    continue
                for x in arr:
                    try:
                        target.add(int(x))
                    except (TypeError, ValueError):
                        pass
    return {
        "stream_ids": stream_ids,
        "movie_ids": movie_ids,
        "radio_stream_ids": radio_stream_ids,
        "series_ids": series_ids,
    }


def _user_owned_by_reseller(user: Optional[User], reseller_id: int) -> bool:
    return user is not None and user.created_by_reseller_id == reseller_id


def _live_stream_dict(s: Stream) -> dict:
    return {
        "id": s.id,
        "stream_display_name": s.stream_display_name,
        "category_id": s.category_id,
        "stream_icon": s.stream_icon,
        "epg_channel_id": s.epg_channel_id,
        "enabled": s.enabled,
    }


def _movie_dict(m: Movie) -> dict:
    return {
        "id": m.id,
        "stream_display_name": m.stream_display_name,
        "category_id": m.category_id,
        "stream_icon": m.stream_icon,
        "rating": m.rating,
        "genre": m.genre,
        "plot": m.plot,
    }


def _reseller_user_ids_set(db: Session, reseller_id: int) -> Set[int]:
    rows = db.query(User.id).filter(User.created_by_reseller_id == reseller_id).all()
    return {r[0] for r in rows}


class ResellerLoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    max_connections: int = 1
    package_id: Optional[int] = None
    bouquet: Optional[str] = None
    exp_date: Optional[datetime] = None
    notes: Optional[str] = None


class ExtendUserRequest(BaseModel):
    user_id: int
    days: int = 30


class DeviceCreateRequest(BaseModel):
    username: str
    password: str
    max_connections: int = 1
    exp_date: Optional[datetime] = None
    enabled: bool = True
    admin_notes: Optional[str] = None
    bouquet: Optional[str] = None
    allowed_ips: Optional[str] = None


class DeviceUpdateRequest(BaseModel):
    password: Optional[str] = None
    max_connections: Optional[int] = None
    exp_date: Optional[datetime] = None
    enabled: Optional[bool] = None
    admin_notes: Optional[str] = None
    bouquet: Optional[str] = None
    allowed_ips: Optional[str] = None


class ResellerTicketCreate(BaseModel):
    subject: str
    message: str
    priority: str = "normal"


class ResellerTicketReply(BaseModel):
    message: str


class ResellerProfileUpdate(BaseModel):
    password: Optional[str] = None
    notes: Optional[str] = None
    allowed_ips: Optional[str] = None


@router.post("/login")
def reseller_login(req: ResellerLoginRequest, db: Session = Depends(get_db)):
    svc = ResellerService(db)
    reseller = svc.authenticate(req.username, req.password)
    if not reseller:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(reseller.id), "role": "reseller"})
    return {
        "access_token": token, "token_type": "bearer",
        "reseller_id": reseller.id, "username": reseller.username,
        "credits": reseller.credits,
    }


@router.get("/info")
def reseller_info(reseller: Reseller = Depends(get_current_reseller)):
    return {
        "id": reseller.id, "username": reseller.username,
        "credits": reseller.credits, "status": reseller.status,
    }


@router.get("/users")
def reseller_users(
    page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), reseller: Reseller = Depends(get_current_reseller),
):
    q = db.query(User).filter(User.created_by_reseller_id == reseller.id)
    total = q.count()
    items = (
        q.order_by(User.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    result = {"items": items, "total": total, "page": page, "per_page": per_page}
    result["items"] = [
        {
            "id": u.id, "username": u.username, "max_connections": u.max_connections,
            "exp_date": str(u.exp_date) if u.exp_date else None,
            "enabled": u.enabled, "is_trial": u.is_trial,
            "created_at": str(u.created_at) if u.created_at else None,
        }
        for u in result["items"]
    ]
    return result


@router.post("/users/create")
def reseller_create_user(
    data: CreateUserRequest, db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    reseller_svc = ResellerService(db)
    user_svc = UserService(db)

    existing = user_svc.get_by_username(data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    cost = 1
    if data.package_id:
        pkg_svc = PackageService(db)
        pkg = pkg_svc.get_by_id(data.package_id)
        if pkg:
            cost = pkg.official_credits or 1
        allowed_pkg = _parse_package_ids(reseller)
        if (
            allowed_pkg is not None
            and data.package_id is not None
            and data.package_id not in allowed_pkg
        ):
            raise HTTPException(status_code=400, detail="Package not allowed for this reseller")

    if reseller.credits < cost:
        raise HTTPException(status_code=400, detail="Insufficient credits")

    user_data = data.model_dump(exclude_none=True)
    user_data.pop("package_id", None)
    if "notes" in user_data:
        user_data["reseller_notes"] = user_data.pop("notes")
    user_data["created_by_reseller_id"] = reseller.id
    user = user_svc.create(user_data)
    reseller_svc.use_credits(reseller.id, cost)

    return {"user_id": user.id, "username": user.username, "credits_remaining": reseller.credits - cost}


@router.post("/users/extend")
def reseller_extend_user(
    data: ExtendUserRequest, db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    user_svc = UserService(db)
    reseller_svc = ResellerService(db)

    user = user_svc.get_by_id(data.user_id)
    if not user or not _user_owned_by_reseller(user, reseller.id):
        raise HTTPException(status_code=404, detail="User not found")

    if reseller.credits < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits")

    new_exp = datetime.now(timezone.utc) + timedelta(days=data.days)
    if user.exp_date and user.exp_date > datetime.now(timezone.utc):
        new_exp = user.exp_date + timedelta(days=data.days)

    user_svc.update(data.user_id, {"exp_date": new_exp})
    reseller_svc.use_credits(reseller.id, 1)

    return {"user_id": user.id, "new_exp_date": str(new_exp)}


@router.delete("/users/{user_id}")
def reseller_delete_user(
    user_id: int, db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    user_svc = UserService(db)
    user = user_svc.get_by_id(user_id)
    if not user or not _user_owned_by_reseller(user, reseller.id):
        raise HTTPException(status_code=404, detail="User not found")
    if not user_svc.delete(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "deleted"}


@router.post("/users/{user_id}/toggle")
def reseller_toggle_user(
    user_id: int, db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    user_svc = UserService(db)
    u = user_svc.get_by_id(user_id)
    if not u or not _user_owned_by_reseller(u, reseller.id):
        raise HTTPException(status_code=404, detail="User not found")
    updated = user_svc.toggle_status(user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": updated.id, "enabled": updated.enabled}


@router.get("/packages")
def reseller_packages(db: Session = Depends(get_db), reseller: Reseller = Depends(get_current_reseller)):
    pkgs = PackageService(db).get_all()
    allowed = _parse_package_ids(reseller)
    if allowed is not None:
        allow_set = set(allowed)
        pkgs = [p for p in pkgs if p.id in allow_set]
    return [
        {
            "id": p.id, "package_name": p.package_name,
            "is_trial": p.is_trial, "trial_credits": p.trial_credits,
            "official_credits": p.official_credits,
            "max_connections": p.max_connections,
        }
        for p in pkgs
    ]


@router.get("/streams")
def reseller_streams(
    category_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    scope = _reseller_content_scope(db, reseller)
    q = db.query(Stream).filter(Stream.stream_type == 1, Stream.enabled.is_(True))
    if category_id is not None:
        q = q.filter(Stream.category_id == category_id)
    if scope is not None:
        ids = scope["stream_ids"]
        if not ids:
            return {"items": [], "total": 0, "page": page, "per_page": per_page}
        q = q.filter(Stream.id.in_(ids))
    total = q.count()
    items = (
        q.order_by(Stream.order.asc(), Stream.id.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_live_stream_dict(s) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/movies")
def reseller_movies(
    category_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    scope = _reseller_content_scope(db, reseller)
    q = db.query(Movie)
    if category_id is not None:
        q = q.filter(Movie.category_id == category_id)
    if scope is not None:
        mids = scope["movie_ids"]
        if not mids:
            return {"items": [], "total": 0, "page": page, "per_page": per_page}
        q = q.filter(Movie.id.in_(mids))
    total = q.count()
    items = (
        q.order_by(Movie.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_movie_dict(m) for m in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/radios")
def reseller_radios(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    scope = _reseller_content_scope(db, reseller)
    q = RadioService(db)._radio_query()
    if scope is not None:
        rids = scope["radio_stream_ids"]
        if not rids:
            return {"items": [], "total": 0, "page": page, "per_page": per_page}
        q = q.filter(Stream.id.in_(rids))
    total = q.count()
    items = (
        q.order_by(Stream.order.asc(), Stream.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_live_stream_dict(s) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/episodes")
def reseller_episodes(
    series_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    scope = _reseller_content_scope(db, reseller)
    q = db.query(SeriesEpisode)
    if series_id is not None:
        q = q.filter(SeriesEpisode.series_id == series_id)
    if scope is not None:
        sids = scope["series_ids"]
        if not sids:
            return {"items": [], "total": 0, "page": page, "per_page": per_page}
        q = q.filter(SeriesEpisode.series_id.in_(sids))
    total = q.count()
    items = (
        q.order_by(SeriesEpisode.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [
            {
                "id": e.id,
                "series_id": e.series_id,
                "stream_display_name": e.stream_display_name,
                "season_number": e.season_number,
                "episode_number": e.episode_number,
                "plot": e.plot,
                "duration": e.duration,
            }
            for e in items
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/created-channels")
def reseller_created_channels(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    scope = _reseller_content_scope(db, reseller)
    q = ChannelService(db)._channel_query()
    if scope is not None:
        cids = scope["stream_ids"]
        if not cids:
            return {"items": [], "total": 0, "page": page, "per_page": per_page}
        q = q.filter(Stream.id.in_(cids))
    total = q.count()
    items = (
        q.order_by(Stream.order.asc(), Stream.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_live_stream_dict(s) for s in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/epg")
def reseller_epg(
    epg_id: Optional[str] = None,
    channel_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    scope = _reseller_content_scope(db, reseller)
    epg_svc = EpgService(db)

    def _rows_to_payload(rows: List[EpgData]) -> List[dict]:
        return [
            {
                "id": p.id,
                "channel_id": p.channel_id,
                "epg_id": p.epg_id,
                "title": p.title,
                "start": str(p.start),
                "end": str(p.end),
                "description": p.description,
            }
            for p in rows
        ]

    if scope is not None:
        ids = scope["stream_ids"]
        if not ids:
            return {"items": [], "total": 0, "page": page, "per_page": per_page}
        if channel_id is not None and channel_id not in ids:
            raise HTTPException(status_code=403, detail="Channel not in your allowed bouquets")
        q = db.query(EpgData).filter(EpgData.channel_id.in_(list(ids)))
        if channel_id is not None:
            q = q.filter(EpgData.channel_id == channel_id)
        if epg_id is not None:
            q = q.filter(EpgData.epg_id == epg_id)
        total = q.count()
        rows = (
            q.order_by(EpgData.start.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {
            "items": _rows_to_payload(rows),
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    data = epg_svc.list_programs(epg_id=epg_id, channel_id=channel_id, page=page, per_page=per_page)
    data["items"] = _rows_to_payload(data["items"])
    return data


@router.get("/lines")
def reseller_lines(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    uid_set = _reseller_user_ids_set(db, reseller.id)
    if not uid_set:
        return {"items": [], "total": 0, "page": page, "per_page": per_page}
    q = db.query(Line).filter(Line.user_id.in_(uid_set))
    total = q.count()
    lines = (
        q.order_by(Line.date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [
            {
                "id": ln.id,
                "user_id": ln.user_id,
                "stream_id": ln.stream_id,
                "server_id": ln.server_id,
                "container": ln.container,
                "user_ip": ln.user_ip,
                "user_agent": ln.user_agent,
                "date": str(ln.date) if ln.date else None,
            }
            for ln in lines
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/lines/{line_id}/activity")
def reseller_line_activity(
    line_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    uid_set = _reseller_user_ids_set(db, reseller.id)
    line = db.query(Line).filter(Line.id == line_id).first()
    if not line or line.user_id not in uid_set:
        raise HTTPException(status_code=404, detail="Line not found")
    acts = (
        db.query(UserActivity)
        .filter(UserActivity.user_id == line.user_id)
        .order_by(UserActivity.date_start.desc())
        .limit(limit)
        .all()
    )
    return {
        "line_id": line_id,
        "user_id": line.user_id,
        "items": [
            {
                "id": a.id,
                "stream_id": a.stream_id,
                "server_id": a.server_id,
                "date_start": str(a.date_start) if a.date_start else None,
                "date_stop": str(a.date_stop) if a.date_stop else None,
                "user_ip": a.user_ip,
                "user_agent": a.user_agent,
                "container": a.container,
            }
            for a in acts
        ],
    }


@router.get("/live-connections")
def reseller_live_connections(
    db: Session = Depends(get_db), reseller: Reseller = Depends(get_current_reseller)
):
    uid_set = _reseller_user_ids_set(db, reseller.id)
    tracker = ConnectionTracker(db)
    conns = [c for c in tracker.get_live_connections() if c.get("user_id") in uid_set]
    return {"connections": conns, "total": len(conns)}


def _device_user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "max_connections": u.max_connections,
        "exp_date": str(u.exp_date) if u.exp_date else None,
        "enabled": u.enabled,
        "admin_notes": u.admin_notes,
        "bouquet": u.bouquet,
        "allowed_ips": u.allowed_ips,
        "is_mag": u.is_mag,
        "is_stalker": u.is_stalker,
        "created_at": str(u.created_at) if u.created_at else None,
    }


@router.get("/mags")
def reseller_list_mags(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    q = db.query(User).filter(
        User.is_mag.is_(True), User.created_by_reseller_id == reseller.id
    )
    if search:
        q = q.filter(User.username.ilike(f"%{search.strip()}%"))
    total = q.count()
    items = (
        q.order_by(User.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_device_user_dict(u) for u in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/mags")
def reseller_create_mag(
    data: DeviceCreateRequest,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    if UserService(db).get_by_username(data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    payload = data.model_dump(exclude_none=True)
    payload["created_by_reseller_id"] = reseller.id
    user = MagService(db).create_mag(payload)
    return _device_user_dict(user)


@router.put("/mags/{user_id}")
def reseller_update_mag(
    user_id: int,
    data: DeviceUpdateRequest,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    u = MagService(db).get_mag_by_id(user_id)
    if not u or not _user_owned_by_reseller(u, reseller.id):
        raise HTTPException(status_code=404, detail="MAG device not found")
    updated = MagService(db).update_mag(user_id, data.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="MAG device not found")
    return _device_user_dict(updated)


@router.delete("/mags/{user_id}")
def reseller_delete_mag(
    user_id: int, db: Session = Depends(get_db), reseller: Reseller = Depends(get_current_reseller)
):
    u = MagService(db).get_mag_by_id(user_id)
    if not u or not _user_owned_by_reseller(u, reseller.id):
        raise HTTPException(status_code=404, detail="MAG device not found")
    if not MagService(db).delete_mag(user_id):
        raise HTTPException(status_code=404, detail="MAG device not found")
    return {"status": "deleted"}


@router.get("/enigmas")
def reseller_list_enigmas(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    q = db.query(User).filter(
        User.is_stalker.is_(True), User.created_by_reseller_id == reseller.id
    )
    if search:
        q = q.filter(User.username.ilike(f"%{search.strip()}%"))
    total = q.count()
    items = (
        q.order_by(User.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        "items": [_device_user_dict(u) for u in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/enigmas")
def reseller_create_enigma(
    data: DeviceCreateRequest,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    if UserService(db).get_by_username(data.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    payload = data.model_dump(exclude_none=True)
    payload["created_by_reseller_id"] = reseller.id
    user = EnigmaService(db).create_enigma(payload)
    return _device_user_dict(user)


@router.put("/enigmas/{user_id}")
def reseller_update_enigma(
    user_id: int,
    data: DeviceUpdateRequest,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    u = EnigmaService(db).get_enigma_by_id(user_id)
    if not u or not _user_owned_by_reseller(u, reseller.id):
        raise HTTPException(status_code=404, detail="Enigma2 device not found")
    updated = EnigmaService(db).update_enigma(user_id, data.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Enigma2 device not found")
    return _device_user_dict(updated)


@router.delete("/enigmas/{user_id}")
def reseller_delete_enigma(
    user_id: int, db: Session = Depends(get_db), reseller: Reseller = Depends(get_current_reseller)
):
    u = EnigmaService(db).get_enigma_by_id(user_id)
    if not u or not _user_owned_by_reseller(u, reseller.id):
        raise HTTPException(status_code=404, detail="Enigma2 device not found")
    if not EnigmaService(db).delete_enigma(user_id):
        raise HTTPException(status_code=404, detail="Enigma2 device not found")
    return {"status": "deleted"}


@router.get("/tickets")
def reseller_list_tickets(
    db: Session = Depends(get_db), reseller: Reseller = Depends(get_current_reseller)
):
    svc = SettingsService(db)
    raw = svc.get(_reseller_ticket_key(reseller.id), "[]")
    tickets = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    return {"tickets": tickets}


@router.post("/tickets")
def reseller_create_ticket(
    data: ResellerTicketCreate,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    svc = SettingsService(db)
    key = _reseller_ticket_key(reseller.id)
    raw = svc.get(key, "[]")
    tickets = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    ticket = {
        "id": len(tickets) + 1,
        "subject": data.subject,
        "message": data.message,
        "priority": data.priority,
        "status": "open",
        "created_by": reseller.username,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "replies": [],
    }
    tickets.append(ticket)
    svc.set(key, tickets, "json")
    return ticket


@router.get("/tickets/{ticket_id}")
def reseller_get_ticket(
    ticket_id: int, db: Session = Depends(get_db), reseller: Reseller = Depends(get_current_reseller)
):
    svc = SettingsService(db)
    raw = svc.get(_reseller_ticket_key(reseller.id), "[]")
    tickets = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    for t in tickets:
        if t.get("id") == ticket_id:
            return t
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.post("/tickets/{ticket_id}/reply")
def reseller_reply_ticket(
    ticket_id: int,
    data: ResellerTicketReply,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    svc = SettingsService(db)
    key = _reseller_ticket_key(reseller.id)
    raw = svc.get(key, "[]")
    tickets = json.loads(raw) if isinstance(raw, str) else raw if isinstance(raw, list) else []
    for t in tickets:
        if t.get("id") == ticket_id:
            t["replies"].append(
                {
                    "message": data.message,
                    "by": reseller.username,
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
            svc.set(key, tickets, "json")
            return t
    raise HTTPException(status_code=404, detail="Ticket not found")


@router.get("/profile")
def reseller_get_profile(reseller: Reseller = Depends(get_current_reseller)):
    return {
        "id": reseller.id,
        "username": reseller.username,
        "credits": reseller.credits,
        "status": reseller.status,
        "notes": reseller.notes,
        "allowed_ips": reseller.allowed_ips,
        "allowed_packages": reseller.allowed_packages,
        "max_credits": reseller.max_credits,
    }


@router.put("/profile")
def reseller_update_profile(
    data: ResellerProfileUpdate,
    db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        return {"status": "unchanged"}
    ResellerService(db).update(reseller.id, payload)
    return {"status": "updated"}
