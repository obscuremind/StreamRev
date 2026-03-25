"""
Xtream Codes compatible Player API.
Endpoints:
  GET /player_api.php?username=X&password=Y                    - Auth + server info
  GET /player_api.php?username=X&password=Y&action=...         - Various actions
  GET /get.php?username=X&password=Y&type=m3u_plus             - M3U playlist
  GET /xmltv.php?username=X&password=Y                         - EPG XML
  GET /{username}/{password}/{stream_id}                       - Stream playback (live)
  GET /movie/{username}/{password}/{stream_id}                 - VOD playback
  GET /series/{username}/{password}/{stream_id}                - Series playback
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone, timedelta
import base64
import json
from src.core.database import get_db
from src.core.config import settings
from src.core.auth.password import verify_password
from src.core.util.encryption import base64_decode
from src.domain.user.service import UserService
from src.domain.stream.service import StreamService
from src.domain.vod.service import MovieService, SeriesService
from src.domain.category.service import CategoryService
from src.domain.epg.service import EpgService
from src.domain.models import User
from src.domain.security.blocklist_service import BlocklistService, BruteforceGuard

router = APIRouter(tags=["Player API"])

ACTION_NUM_ALIASES = {
    "200": "get_vod_categories",
    "201": "get_live_categories",
    "202": "get_live_streams",
    "203": "get_vod_streams",
    "204": "get_series_info",
    "205": "get_short_epg",
    "206": "get_series_categories",
    "207": "get_simple_data_table",
    "208": "get_series",
    "209": "get_vod_info",
}


def _parse_epg_range_time(raw: Optional[str]) -> Optional[datetime]:
    if raw is None or raw == "":
        return None
    try:
        return datetime.utcfromtimestamp(int(raw))
    except (ValueError, TypeError):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            return None


def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host or ""
    return ""


def _dt_to_unix(dt: Optional[datetime]) -> int:
    if not dt:
        return 0
    if dt.tzinfo is None:
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    return int(dt.timestamp())


def _normalize_action(action: Optional[str]) -> Optional[str]:
    if action is None:
        return None
    s = str(action).strip()
    if s.isdigit():
        return ACTION_NUM_ALIASES.get(s, s)
    return s


def _user_from_token(db: Session, token: str) -> Optional[User]:
    user = db.query(User).filter(User.player_api_token == token).first()
    if user:
        return user
    decoded = base64_decode(token)
    if not decoded:
        return None
    for sep in (":", "|"):
        if sep in decoded:
            u, p = decoded.split(sep, 1)
            u, p = u.strip(), p.strip()
            if u and p:
                cand = db.query(User).filter(User.username == u).first()
                if cand and verify_password(p, cand.password):
                    return cand
    return None


def _ensure_user_active(user: User, db: Session) -> None:
    if not user.enabled:
        raise HTTPException(status_code=403, detail="Account disabled")
    svc = UserService(db)
    if svc.is_expired(user):
        raise HTTPException(status_code=403, detail="Account expired")


def _authenticate_user(
    request: Request,
    username: Optional[str],
    password: Optional[str],
    token: Optional[str],
    db: Session,
) -> User:
    ip = _client_ip(request)
    blocklist = BlocklistService(db)
    if blocklist.is_ip_blocked(ip):
        raise HTTPException(status_code=403, detail="Access denied")
    guard = BruteforceGuard(db)
    if guard.is_blocked(ip):
        raise HTTPException(status_code=403, detail="Too many failed login attempts")

    if token and str(token).strip():
        user = _user_from_token(db, str(token).strip())
        if user:
            _ensure_user_active(user, db)
            guard.record_attempt(ip, True)
            return user
        guard.record_attempt(ip, False)
        raise HTTPException(status_code=403, detail="Invalid credentials")

    if not username or not password:
        raise HTTPException(status_code=403, detail="Invalid credentials")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password):
        guard.record_attempt(ip, False)
        raise HTTPException(status_code=403, detail="Invalid credentials")
    if not user.enabled:
        guard.record_attempt(ip, False)
        raise HTTPException(status_code=403, detail="Account disabled")
    svc = UserService(db)
    if svc.is_expired(user):
        guard.record_attempt(ip, False)
        raise HTTPException(status_code=403, detail="Account expired")
    guard.record_attempt(ip, True)
    return user


def _parse_pagination(offset: Optional[str], items_per_page: Optional[str]) -> tuple[int, int]:
    try:
        off = max(0, int(offset)) if offset not in (None, "") else 0
    except (ValueError, TypeError):
        off = 0
    try:
        ipp = int(items_per_page) if items_per_page not in (None, "") else 10_000
    except (ValueError, TypeError):
        ipp = 10_000
    ipp = max(1, min(ipp, 10_000))
    return off, ipp


def _epg_listing_full(p, stream, now_utc: datetime) -> dict:
    start_ts = _dt_to_unix(p.start)
    end_ts = _dt_to_unix(p.end)
    now_playing = 0
    if p.start and p.end and p.start <= now_utc <= p.end:
        now_playing = 1
    has_archive = 1 if (stream and getattr(stream, "tv_archive", False)) else 0
    title = p.title or ""
    desc = p.description or ""
    return {
        "id": str(p.id),
        "epg_id": p.epg_id,
        "title": base64.b64encode(title.encode("utf-8")).decode("ascii"),
        "lang": p.lang or "en",
        "start": p.start.strftime("%Y-%m-%d %H:%M:%S") if p.start else "",
        "end": p.end.strftime("%Y-%m-%d %H:%M:%S") if p.end else "",
        "description": base64.b64encode(desc.encode("utf-8")).decode("ascii"),
        "channel_id": str(p.channel_id) if p.channel_id is not None else "",
        "start_timestamp": start_ts,
        "stop_timestamp": end_ts,
        "now_playing": now_playing,
        "has_archive": has_archive,
    }


def _epg_listing_short(p, stream, now_utc: datetime) -> dict:
    row = _epg_listing_full(p, stream, now_utc)
    row["end_timestamp"] = row["stop_timestamp"]
    return row


def _get_server_info(user: User) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "user_info": {
            "username": user.username,
            "password": "***",
            "message": "",
            "auth": 1,
            "status": "Active",
            "exp_date": str(int(user.exp_date.timestamp())) if user.exp_date else None,
            "is_trial": "1" if user.is_trial else "0",
            "active_cons": "0",
            "created_at": str(int(user.created_at.timestamp())) if user.created_at else None,
            "max_connections": str(user.max_connections),
            "allowed_output_formats": ["ts", "m3u8", "rtmp"],
        },
        "server_info": {
            "url": settings.SERVER_HOST,
            "port": str(settings.SERVER_PORT),
            "https_port": str(settings.SERVER_PORT),
            "server_protocol": settings.SERVER_PROTOCOL,
            "rtmp_port": "8880",
            "timezone": "UTC",
            "timestamp_now": int(now.timestamp()),
            "time_now": now.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }


@router.get("/player_api.php")
@router.get("/panel_api/player_api.php")
def player_api(
    request: Request,
    username: Optional[str] = Query(None),
    password: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    stream_id: Optional[str] = Query(None),
    vod_id: Optional[str] = Query(None),
    series_id: Optional[str] = Query(None),
    limit: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    offset: Optional[str] = Query(None),
    items_per_page: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    user = _authenticate_user(request, username, password, token, db)
    action = _normalize_action(action)
    if not action:
        return _get_server_info(user)

    cat_svc = CategoryService(db)
    stream_svc = StreamService(db)
    movie_svc = MovieService(db)
    series_svc = SeriesService(db)
    epg_svc = EpgService(db)
    off, ipp = _parse_pagination(offset, items_per_page)

    if action == "get_live_categories":
        live_cats = cat_svc.get_live_categories()
        radio_cats = cat_svc.get_radio_categories()
        seen: set[int] = set()
        merged = []
        for c in live_cats + radio_cats:
            if c.id in seen:
                continue
            seen.add(c.id)
            merged.append(c)
        return [{"category_id": str(c.id), "category_name": c.category_name, "parent_id": c.parent_id or 0} for c in merged]

    elif action == "get_vod_categories":
        cats = cat_svc.get_movie_categories()
        return [{"category_id": str(c.id), "category_name": c.category_name, "parent_id": c.parent_id or 0} for c in cats]

    elif action == "get_series_categories":
        cats = cat_svc.get_series_categories()
        return [{"category_id": str(c.id), "category_name": c.category_name, "parent_id": c.parent_id or 0} for c in cats]

    elif action == "get_live_streams":
        cat_id = int(category_id) if category_id else None
        streams_all = stream_svc.get_live_streams(category_id=cat_id)
        streams = streams_all[off : off + ipp]
        return [
            {
                "num": off + i + 1, "name": s.stream_display_name, "stream_type": "live",
                "stream_id": s.id, "stream_icon": s.stream_icon or "",
                "epg_channel_id": s.epg_channel_id or "", "added": str(int(s.added.timestamp())) if s.added else "0",
                "category_id": str(s.category_id) if s.category_id else "0",
                "tv_archive": 1 if s.tv_archive else 0,
                "direct_source": "", "tv_archive_duration": s.tv_archive_duration or 0,
            }
            for i, s in enumerate(streams)
        ]

    elif action == "get_vod_streams":
        cat_id = int(category_id) if category_id else None
        result = movie_svc.get_all(category_id=cat_id, per_page=500_000)
        items = result["items"][off : off + ipp]
        return [
            {
                "num": off + i + 1, "name": m.stream_display_name, "stream_type": "movie",
                "stream_id": m.id, "stream_icon": m.stream_icon or "",
                "rating": str(m.rating or ""), "rating_5based": m.rating_5based or 0,
                "added": str(int(m.added.timestamp())) if m.added else "0",
                "category_id": str(m.category_id) if m.category_id else "0",
                "container_extension": m.container_extension or "mp4",
                "direct_source": "",
            }
            for i, m in enumerate(items)
        ]

    elif action == "get_series":
        cat_id = int(category_id) if category_id else None
        result = series_svc.get_all(category_id=cat_id, per_page=500_000)
        items = result["items"][off : off + ipp]
        return [
            {
                "series_id": s.id, "name": s.title, "cover": s.cover or "",
                "plot": s.plot or "", "cast": s.cast or "", "director": s.director or "",
                "genre": s.genre or "", "release_date": s.release_date or "",
                "rating": str(s.rating or ""), "rating_5based": s.rating_5based or 0,
                "backdrop_path": json.dumps([s.backdrop_path]) if s.backdrop_path else "[]",
                "youtube_trailer": s.youtube_trailer or "",
                "category_id": str(s.category_id) if s.category_id else "0",
                "last_modified": str(int(s.last_modified.timestamp())) if s.last_modified else "0",
            }
            for s in items
        ]

    elif action == "get_series_info":
        if not series_id:
            raise HTTPException(status_code=400, detail="series_id required")
        series = series_svc.get_by_id(int(series_id))
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        episodes = series_svc.get_episodes(int(series_id))
        seasons = {}
        for ep in episodes:
            sn = str(ep.season_number or 1)
            if sn not in seasons:
                seasons[sn] = []
            seasons[sn].append({
                "id": str(ep.id), "episode_num": ep.episode_number,
                "title": ep.stream_display_name or "",
                "container_extension": ep.container_extension or "mp4",
                "info": {"plot": ep.plot or "", "duration_secs": ep.duration or 0, "rating": ep.rating or 0,
                         "movie_image": ep.movie_image or ""},
                "added": str(int(ep.added.timestamp())) if ep.added else "0",
                "season": int(sn), "direct_source": "",
            })
        return {
            "seasons": seasons,
            "info": {
                "name": series.title, "cover": series.cover or "",
                "plot": series.plot or "", "cast": series.cast or "",
                "director": series.director or "", "genre": series.genre or "",
                "release_date": series.release_date or "",
                "backdrop_path": json.dumps([series.backdrop_path]) if series.backdrop_path else "[]",
                "youtube_trailer": series.youtube_trailer or "",
                "rating": str(series.rating or ""), "rating_5based": series.rating_5based or 0,
                "category_id": str(series.category_id) if series.category_id else "0",
            },
            "episodes": seasons,
        }

    elif action == "get_vod_info":
        if not vod_id:
            raise HTTPException(status_code=400, detail="vod_id required")
        movie = movie_svc.get_by_id(int(vod_id))
        if not movie:
            raise HTTPException(status_code=404, detail="VOD not found")
        return {
            "info": {
                "movie_image": movie.stream_icon or "",
                "name": movie.stream_display_name,
                "plot": movie.plot or "",
                "cast": movie.cast or "",
                "director": movie.director or "",
                "genre": movie.genre or "",
                "release_date": movie.release_date or "",
                "rating": str(movie.rating or ""),
                "backdrop_path": json.dumps([movie.backdrop_path]) if movie.backdrop_path else "[]",
                "youtube_trailer": movie.youtube_trailer or "",
                "duration_secs": movie.episode_run_time or 0,
                "category_id": str(movie.category_id) if movie.category_id else "0",
            },
            "movie_data": {
                "stream_id": movie.id,
                "name": movie.stream_display_name,
                "added": str(int(movie.added.timestamp())) if movie.added else "0",
                "category_id": str(movie.category_id) if movie.category_id else "0",
                "container_extension": movie.container_extension or "mp4",
                "direct_source": "",
                "custom_sid": movie.custom_sid or "",
            },
        }

    elif action == "get_short_epg":
        if not stream_id:
            raise HTTPException(status_code=400, detail="stream_id required")
        stream = stream_svc.get_by_id(int(stream_id))
        if not stream or not stream.epg_channel_id:
            return {"epg_listings": []}
        programs = epg_svc.get_programs(stream.epg_channel_id, limit=10)
        now_utc = datetime.utcnow()
        return {
            "epg_listings": [
                _epg_listing_short(p, stream, now_utc)
                for p in programs
            ]
        }

    elif action == "get_epg":
        if not stream_id:
            raise HTTPException(status_code=400, detail="stream_id required")
        stream = stream_svc.get_by_id(int(stream_id))
        if not stream or not stream.epg_channel_id:
            return {"epg_listings": []}
        now = datetime.utcnow()
        range_start = _parse_epg_range_time(start) or now
        range_end = _parse_epg_range_time(end) or (now + timedelta(days=7))
        if range_end <= range_start:
            range_end = range_start + timedelta(days=1)
        programs = epg_svc.get_programs_in_range(
            stream.epg_channel_id,
            range_start=range_start,
            range_end=range_end,
        )
        now_utc = datetime.utcnow()
        return {
            "epg_listings": [
                _epg_listing_full(p, stream, now_utc)
                for p in programs
            ]
        }

    elif action == "get_simple_data_table":
        streams = stream_svc.get_live_streams()
        result = movie_svc.get_all(per_page=500_000)
        movies = result["items"]
        if stream_id:
            stream = stream_svc.get_by_id(int(stream_id))
            if stream and stream.epg_channel_id:
                now_utc = datetime.utcnow()
                range_start = now_utc - timedelta(hours=6)
                range_end = now_utc + timedelta(days=2)
                programs = epg_svc.get_programs_in_range(
                    stream.epg_channel_id,
                    range_start=range_start,
                    range_end=range_end,
                )
                listings = [_epg_listing_full(p, stream, now_utc) for p in programs]
            else:
                listings = []
            return {
                "epg_listings": listings,
                "total_live": len(streams),
                "total_vod": len(movies),
            }
        return {
            "epg_listings": {},
            "total_live": len(streams),
            "total_vod": len(movies),
        }

    return {"error": "Unknown action"}


@router.get("/get.php")
@router.get("/panel_api/get.php")
def get_playlist(
    request: Request,
    username: Optional[str] = Query(None),
    password: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    type: str = Query("m3u_plus"),
    output: str = Query("ts"),
    db: Session = Depends(get_db),
):
    user = _authenticate_user(request, username, password, token, db)
    stream_svc = StreamService(db)
    cat_svc = CategoryService(db)
    movie_svc = MovieService(db)

    base_url = str(request.base_url).rstrip("/")

    lines = ['#EXTM3U']

    categories = {c.id: c.category_name for c in cat_svc.get_all()}
    streams = stream_svc.get_live_streams()
    for s in streams:
        cat_name = categories.get(s.category_id, "Uncategorized")
        tvg_id = s.epg_channel_id or ""
        tvg_logo = s.stream_icon or ""
        lines.append(
            f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{s.stream_display_name}" '
            f'tvg-logo="{tvg_logo}" group-title="{cat_name}",{s.stream_display_name}'
        )
        lines.append(f'{base_url}/live/{username}/{password}/{s.id}.{output}')

    result = movie_svc.get_all(per_page=10000)
    for m in result["items"]:
        cat_name = categories.get(m.category_id, "VOD")
        lines.append(
            f'#EXTINF:-1 tvg-name="{m.stream_display_name}" '
            f'tvg-logo="{m.stream_icon or ""}" group-title="{cat_name}",{m.stream_display_name}'
        )
        ext = m.container_extension or "mp4"
        lines.append(f'{base_url}/movie/{username}/{password}/{m.id}.{ext}')

    content = "\n".join(lines)
    return Response(content=content, media_type="audio/x-mpegurl",
                    headers={"Content-Disposition": f'attachment; filename="{username}_playlist.m3u"'})


@router.get("/xmltv.php")
@router.get("/panel_api/xmltv.php")
def get_epg_xml(
    request: Request,
    username: Optional[str] = Query(None),
    password: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    user = _authenticate_user(request, username, password, token, db)
    stream_svc = StreamService(db)
    epg_svc = EpgService(db)

    streams = stream_svc.get_live_streams()
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<tv>']

    for s in streams:
        if s.epg_channel_id:
            xml_lines.append(f'  <channel id="{s.epg_channel_id}">')
            xml_lines.append(f'    <display-name>{s.stream_display_name}</display-name>')
            if s.stream_icon:
                xml_lines.append(f'    <icon src="{s.stream_icon}" />')
            xml_lines.append('  </channel>')

    for s in streams:
        if s.epg_channel_id:
            programs = epg_svc.get_all_programs(s.epg_channel_id)
            for p in programs:
                start = p.start.strftime("%Y%m%d%H%M%S +0000") if p.start else ""
                stop = p.end.strftime("%Y%m%d%H%M%S +0000") if p.end else ""
                xml_lines.append(f'  <programme start="{start}" stop="{stop}" channel="{p.epg_id}">')
                xml_lines.append(f'    <title lang="{p.lang or "en"}">{p.title or ""}</title>')
                if p.description:
                    xml_lines.append(f'    <desc lang="{p.lang or "en"}">{p.description}</desc>')
                xml_lines.append('  </programme>')

    xml_lines.append('</tv>')
    content = "\n".join(xml_lines)
    return Response(content=content, media_type="application/xml")
