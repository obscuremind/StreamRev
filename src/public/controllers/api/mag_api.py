"""
MAG / Stalker Mini Middleware compatible portal API.

Endpoints mirror legacy PHP paths: ``portal.php`` and ``stalker_portal/server/load.php``.
Dispatch uses query parameters ``type`` and ``action``.
"""

from __future__ import annotations

import json
import re
import secrets
import time
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.core.auth.password import verify_password
from src.core.config import settings
from src.core.database import get_db
from src.domain.category.service import CategoryService
from src.domain.epg.service import EpgService
from src.domain.models import (
    Bouquet,
    EpgData,
    Movie,
    Series,
    Stream,
    StreamCategory,
    User,
)
from src.domain.stream.service import StreamService
from src.domain.user.service import UserService
from src.domain.vod.service import MovieService, SeriesService

router = APIRouter(tags=["MAG / Stalker API"])


def _ok(js: Any) -> Dict[str, Any]:
    return {"js": js, "status": 1}


def _fail(msg: str) -> Dict[str, Any]:
    return {"js": None, "status": 0, "msg": msg}


def _normalize_mac(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    s = value.strip().upper().replace("-", ":").replace(" ", "")
    if re.fullmatch(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", s):
        return s
    if re.fullmatch(r"[0-9A-F]{12}", s):
        return ":".join(s[i : i + 2] for i in range(0, 12, 2))
    return None


def _mac_from_forwarded(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    for part in value.split(","):
        part = part.strip()
        m = _normalize_mac(part)
        if m:
            return m
    return None


def _extract_mac(
    request: Request,
    mac_query: Optional[str],
) -> Optional[str]:
    if mac_query:
        m = _normalize_mac(mac_query)
        if m:
            return m
    cookie_mac = request.cookies.get("mac")
    if cookie_mac:
        m = _normalize_mac(cookie_mac)
        if m:
            return m
    hdr = request.headers.get("X-Forwarded-For") or request.headers.get("x-forwarded-for")
    return _mac_from_forwarded(hdr)


def _parse_json_ids(raw: Optional[str]) -> List[int]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        out: List[int] = []
        for x in data:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return out
    except (json.JSONDecodeError, TypeError):
        return []


def _bouquet_restrictions(
    db: Session, user: User
) -> Tuple[Optional[Set[int]], Optional[Set[int]], Optional[Set[int]]]:
    """
    Returns (live_ids, movie_ids, series_ids).
    None for a slot means no bouquet restriction for that media type.
    Empty set means explicitly no items allowed for that type.
    """
    raw = (user.bouquet or "").strip()
    if not raw:
        return None, None, None

    live: Set[int] = set()
    movies: Set[int] = set()
    series: Set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            bid = int(part)
        except ValueError:
            continue
        b = db.query(Bouquet).filter(Bouquet.id == bid).first()
        if not b:
            continue
        live.update(_parse_json_ids(b.bouquet_channels))
        movies.update(_parse_json_ids(b.bouquet_movies))
        series.update(_parse_json_ids(b.bouquet_series))

    return live, movies, series


def _resolve_playback_password(
    user: User,
    query_params: Dict[str, Any],
    auth_plain_password: Optional[str],
) -> Optional[str]:
    if auth_plain_password and verify_password(auth_plain_password, user.password):
        return auth_plain_password
    for key in ("playback_password", "password"):
        val = query_params.get(key)
        if val and verify_password(str(val), user.password):
            return str(val)
    return None


def _find_mag_user(
    db: Session,
    mac: Optional[str],
    username: Optional[str],
    password: Optional[str],
) -> Optional[User]:
    q = db.query(User).filter(
        User.enabled.is_(True),
        or_(User.is_mag.is_(True), User.is_stalker.is_(True)),
    )

    if mac:
        norm = _normalize_mac(mac)
        if not norm:
            return None
        for u in q.all():
            un = (u.username or "").strip().upper().replace("-", ":")
            if un == norm:
                return u
            if u.allowed_ips:
                for token in u.allowed_ips.split(","):
                    t = _normalize_mac(token.strip())
                    if t and t == norm:
                        return u
        return None

    if username and password:
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.enabled:
            return None
        if not (user.is_mag or user.is_stalker):
            return None
        if not verify_password(password, user.password):
            return None
        return user

    return None


def _ensure_account_ok(user: User, user_svc: UserService) -> Optional[str]:
    if user_svc.is_expired(user):
        return "Account expired"
    return None


def _filter_live_streams(
    streams: List[Stream], allowed: Optional[Set[int]]
) -> List[Stream]:
    if allowed is None:
        return streams
    return [s for s in streams if s.id in allowed]


def _live_streams_for_user(db: Session, user: User) -> List[Stream]:
    stream_svc = StreamService(db)
    live, _, _ = _bouquet_restrictions(db, user)
    streams = stream_svc.get_live_streams()
    return _filter_live_streams(streams, live)


def _parse_stream_id_from_cmd(cmd: Optional[str]) -> Optional[int]:
    if cmd is None or (isinstance(cmd, str) and not cmd.strip()):
        return None
    s = str(cmd).strip()
    if s.isdigit():
        return int(s)
    m = re.search(r"/ch/(\d+)", s, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"ch_id=(\d+)", s, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{1,10})", s)
    return int(m.group(1)) if m else None


def _playback_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _handshake_token(user: User, mac: str) -> str:
    payload = f"{user.id}:{mac}:{settings.SECRET_KEY}:{int(time.time())}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _dispatch_stalker(
    request: Request,
    db: Session,
    type_: str,
    action: str,
    user: User,
    mac: str,
    query_params: Dict[str, Any],
    auth_plain_password: Optional[str],
) -> Dict[str, Any]:
    t = (type_ or "").strip().lower()
    a = (action or "").strip().lower()
    key = f"{t}/{a}"

    user_svc = UserService(db)
    stream_svc = StreamService(db)
    cat_svc = CategoryService(db)
    movie_svc = MovieService(db)
    series_svc = SeriesService(db)
    epg_svc = EpgService(db)

    err = _ensure_account_ok(user, user_svc)
    if err:
        return _fail(err)

    live_ids, movie_ids, series_ids = _bouquet_restrictions(db, user)

    if key == "stb/handshake":
        token = _handshake_token(user, mac)
        rnd = secrets.token_hex(16)
        return _ok(
            {
                "token": token,
                "random": rnd,
                "not_valid": 0,
                "login": user.username,
            }
        )

    if key == "stb/get_profile":
        exp = (
            str(int(user.exp_date.timestamp()))
            if user.exp_date
            else "0"
        )
        return _ok(
            {
                "login": user.username,
                "password": "***",
                "phone": "",
                "expire_billing_date": exp,
                "max_connection": str(user.max_connections),
                "tariff_plan_name": "IPTV",
                "confirmation_code": "",
                "settings": {},
                "is_android": False,
                "client_type": "STB",
            }
        )

    if key == "itv/get_genres":
        cats: List[StreamCategory] = cat_svc.get_live_categories()
        if live_ids is not None:
            live_streams = _live_streams_for_user(db, user)
            cat_has = {s.category_id for s in live_streams if s.category_id is not None}
            cats = [c for c in cats if c.id in cat_has]
        data = [
            {
                "id": str(c.id),
                "title": c.category_name,
                "alias": str(c.id),
                "censored": 0,
            }
            for c in cats
        ]
        return _ok({"data": data})

    if key == "itv/get_ordered_list":
        try:
            page = max(1, int(query_params.get("p") or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            per_page = min(200, max(1, int(query_params.get("n") or 50)))
        except (TypeError, ValueError):
            per_page = 50
        genre = query_params.get("genre") or query_params.get("category_id")
        category_id: Optional[int] = None
        if genre not in (None, "", "*", "0", 0):
            try:
                category_id = int(genre)
            except (TypeError, ValueError):
                category_id = None

        streams = _live_streams_for_user(db, user)
        if category_id is not None:
            streams = [s for s in streams if s.category_id == category_id]

        total = len(streams)
        start = (page - 1) * per_page
        chunk = streams[start : start + per_page]

        data = []
        for idx, s in enumerate(chunk, start=start + 1):
            data.append(
                {
                    "id": str(s.id),
                    "number": str(idx),
                    "name": s.stream_display_name,
                    "cmd": f"/ch/{s.id}",
                    "logo": s.stream_icon or "",
                    "tv_archive": 1 if s.tv_archive else 0,
                    "tv_archive_duration": s.tv_archive_duration or 0,
                    "category_id": str(s.category_id or 0),
                    "epg_channel_id": s.epg_channel_id or "",
                }
            )
        return _ok({"data": data, "total_items": total, "max_page_items": per_page})

    if key == "itv/create_link":
        cmd = query_params.get("cmd")
        sid = _parse_stream_id_from_cmd(cmd)
        if sid is None:
            return _fail("Invalid cmd")
        stream = stream_svc.get_by_id(sid)
        if not stream or not stream.enabled or stream.stream_type != 1:
            return _fail("Stream not found")
        if live_ids is not None and sid not in live_ids:
            return _fail("Forbidden")
        plain = _resolve_playback_password(user, query_params, auth_plain_password)
        if not plain:
            return _fail(
                "Line password required: pass verified `password` or `playback_password` query parameter"
            )
        base = _playback_base_url(request)
        url = f"{base}/live/{quote(user.username, safe='')}/{quote(plain, safe='')}/{sid}.ts"
        return _ok({"url": url, "cmd": cmd, "stream_id": str(sid)})

    if key in ("epg/get_short_epg", "epg/get_epg"):
        stream_id = query_params.get("stream_id") or query_params.get("ch_id") or query_params.get("id")
        if not stream_id:
            return _fail("stream_id required")
        try:
            sid = int(stream_id)
        except (TypeError, ValueError):
            return _fail("Invalid stream_id")
        stream = stream_svc.get_by_id(sid)
        if not stream or not stream.epg_channel_id:
            return _ok({"data": []})
        if live_ids is not None and sid not in live_ids:
            return _fail("Forbidden")

        limit = 10 if key == "epg/get_short_epg" else 100
        programs: List[EpgData]
        if key == "epg/get_epg":
            programs = epg_svc.get_all_programs(stream.epg_channel_id)
            programs = programs[:limit]
        else:
            programs = epg_svc.get_programs(stream.epg_channel_id, limit=limit)

        data = [
            {
                "id": str(p.id),
                "ch_id": str(sid),
                "epg_id": p.epg_id or "",
                "title": p.title or "",
                "lang": p.lang or "en",
                "start": p.start.strftime("%Y-%m-%d %H:%M:%S") if p.start else "",
                "end": p.end.strftime("%Y-%m-%d %H:%M:%S") if p.end else "",
                "description": p.description or "",
            }
            for p in programs
        ]
        return _ok({"data": data})

    if key in ("vod/get_categories", "vod/get_vod_categories"):
        cats = cat_svc.get_movie_categories()
        if movie_ids is not None:
            q = db.query(Movie.category_id).filter(Movie.id.in_(movie_ids))
            keep = {r[0] for r in q.all() if r[0] is not None}
            cats = [c for c in cats if c.id in keep]
        data = [{"id": str(c.id), "title": c.category_name, "alias": str(c.id)} for c in cats]
        return _ok({"data": data})

    if key == "vod/get_ordered_list":
        try:
            page = max(1, int(query_params.get("p") or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            per_page = min(200, max(1, int(query_params.get("n") or 50)))
        except (TypeError, ValueError):
            per_page = 50
        genre = query_params.get("genre") or query_params.get("category_id")
        cat_id: Optional[int] = None
        if genre not in (None, "", "*", "0", 0):
            try:
                cat_id = int(genre)
            except (TypeError, ValueError):
                cat_id = None

        q = db.query(Movie)
        if movie_ids is not None:
            if not movie_ids:
                return _ok({"data": [], "total_items": 0})
            q = q.filter(Movie.id.in_(movie_ids))
        if cat_id is not None:
            q = q.filter(Movie.category_id == cat_id)
        total = q.count()
        items = (
            q.order_by(Movie.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        data = [
            {
                "id": str(m.id),
                "name": m.stream_display_name,
                "description": m.plot or "",
                "pic": m.stream_icon or "",
                "category_id": str(m.category_id or 0),
                "year": m.release_date or "",
                "rating": str(m.rating or ""),
                "duration": m.episode_run_time or 0,
                "cmd": f"/media/file_{m.id}.mp4",
            }
            for m in items
        ]
        return _ok({"data": data, "total_items": total})

    if key in ("series/get_categories", "series/get_series_categories"):
        cats = cat_svc.get_series_categories()
        if series_ids is not None:
            q = db.query(Series.category_id).filter(Series.id.in_(series_ids))
            keep = {r[0] for r in q.all() if r[0] is not None}
            cats = [c for c in cats if c.id in keep]
        data = [{"id": str(c.id), "title": c.category_name, "alias": str(c.id)} for c in cats]
        return _ok({"data": data})

    if key == "series/get_ordered_list":
        try:
            page = max(1, int(query_params.get("p") or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            per_page = min(200, max(1, int(query_params.get("n") or 50)))
        except (TypeError, ValueError):
            per_page = 50
        genre = query_params.get("genre") or query_params.get("category_id")
        cat_id = None
        if genre not in (None, "", "*", "0", 0):
            try:
                cat_id = int(genre)
            except (TypeError, ValueError):
                cat_id = None

        q = db.query(Series)
        if series_ids is not None:
            if not series_ids:
                return _ok({"data": [], "total_items": 0})
            q = q.filter(Series.id.in_(series_ids))
        if cat_id is not None:
            q = q.filter(Series.category_id == cat_id)
        total = q.count()
        items = (
            q.order_by(Series.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        data = [
            {
                "id": str(s.id),
                "name": s.title,
                "cover": s.cover or "",
                "plot": s.plot or "",
                "category_id": str(s.category_id or 0),
                "rating": str(s.rating or ""),
                "year": s.release_date or "",
            }
            for s in items
        ]
        return _ok({"data": data, "total_items": total})

    return _fail(f"Unsupported action: {type_}/{action}")


@router.get("/portal.php")
@router.get("/stalker_portal/server/load.php")
def stalker_portal(
    request: Request,
    db: Session = Depends(get_db),
    type: Optional[str] = Query(None, alias="type"),
    action: Optional[str] = Query(None, alias="action"),
    mac: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    password: Optional[str] = Query(None),
):
    mac_resolved = _extract_mac(request, mac)
    auth_plain_password: Optional[str] = None
    user: Optional[User] = None
    if mac_resolved:
        user = _find_mag_user(db, mac_resolved, None, None)
    if user is None and username and password:
        user = _find_mag_user(db, None, username, password)
        if user:
            auth_plain_password = password

    if not user:
        return _fail("Authentication failed")

    mac_for_token = mac_resolved or (user.username or "")
    qp = dict(request.query_params)
    body = _dispatch_stalker(
        request,
        db,
        type or "",
        action or "",
        user,
        mac_for_token,
        qp,
        auth_plain_password,
    )
    return Response(
        content=json.dumps(body, ensure_ascii=False),
        media_type="application/json",
    )
