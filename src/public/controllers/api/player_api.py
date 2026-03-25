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
from datetime import datetime, timezone
import json
from src.core.database import get_db
from src.core.config import settings
from src.domain.user.service import UserService
from src.domain.stream.service import StreamService
from src.domain.vod.service import MovieService, SeriesService
from src.domain.category.service import CategoryService
from src.domain.epg.service import EpgService
from src.domain.models import User

router = APIRouter(tags=["Player API"])


def _authenticate_user(username: str, password: str, db: Session) -> User:
    from src.core.auth.password import verify_password
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=403, detail="Invalid credentials")
    if not verify_password(password, user.password):
        raise HTTPException(status_code=403, detail="Invalid credentials")
    if not user.enabled:
        raise HTTPException(status_code=403, detail="Account disabled")
    svc = UserService(db)
    if svc.is_expired(user):
        raise HTTPException(status_code=403, detail="Account expired")
    return user


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
def player_api(
    username: str = Query(...), password: str = Query(...),
    action: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    stream_id: Optional[str] = Query(None),
    vod_id: Optional[str] = Query(None),
    series_id: Optional[str] = Query(None),
    limit: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    user = _authenticate_user(username, password, db)
    if not action:
        return _get_server_info(user)

    cat_svc = CategoryService(db)
    stream_svc = StreamService(db)
    movie_svc = MovieService(db)
    series_svc = SeriesService(db)
    epg_svc = EpgService(db)

    if action == "get_live_categories":
        cats = cat_svc.get_live_categories()
        return [{"category_id": str(c.id), "category_name": c.category_name, "parent_id": c.parent_id or 0} for c in cats]

    elif action == "get_vod_categories":
        cats = cat_svc.get_movie_categories()
        return [{"category_id": str(c.id), "category_name": c.category_name, "parent_id": c.parent_id or 0} for c in cats]

    elif action == "get_series_categories":
        cats = cat_svc.get_series_categories()
        return [{"category_id": str(c.id), "category_name": c.category_name, "parent_id": c.parent_id or 0} for c in cats]

    elif action == "get_live_streams":
        cat_id = int(category_id) if category_id else None
        streams = stream_svc.get_live_streams(category_id=cat_id)
        return [
            {
                "num": i + 1, "name": s.stream_display_name, "stream_type": "live",
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
        result = movie_svc.get_all(category_id=cat_id, per_page=500)
        return [
            {
                "num": i + 1, "name": m.stream_display_name, "stream_type": "movie",
                "stream_id": m.id, "stream_icon": m.stream_icon or "",
                "rating": str(m.rating or ""), "rating_5based": m.rating_5based or 0,
                "added": str(int(m.added.timestamp())) if m.added else "0",
                "category_id": str(m.category_id) if m.category_id else "0",
                "container_extension": m.container_extension or "mp4",
                "direct_source": "",
            }
            for i, m in enumerate(result["items"])
        ]

    elif action == "get_series":
        cat_id = int(category_id) if category_id else None
        result = series_svc.get_all(category_id=cat_id, per_page=500)
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
            for s in result["items"]
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

    elif action == "get_short_epg":
        if not stream_id:
            raise HTTPException(status_code=400, detail="stream_id required")
        stream = stream_svc.get_by_id(int(stream_id))
        if not stream or not stream.epg_channel_id:
            return {"epg_listings": []}
        programs = epg_svc.get_programs(stream.epg_channel_id, limit=10)
        return {
            "epg_listings": [
                {
                    "id": str(p.id), "epg_id": p.epg_id, "title": p.title or "",
                    "lang": p.lang or "en",
                    "start": p.start.strftime("%Y-%m-%d %H:%M:%S") if p.start else "",
                    "end": p.end.strftime("%Y-%m-%d %H:%M:%S") if p.end else "",
                    "description": p.description or "",
                    "channel_id": p.channel_id or "",
                }
                for p in programs
            ]
        }

    elif action == "get_simple_data_table":
        streams = stream_svc.get_live_streams()
        result = movie_svc.get_all(per_page=1000)
        movies = result["items"]
        return {
            "epg_listings": {},
            "total_live": len(streams),
            "total_vod": len(movies),
        }

    return {"error": "Unknown action"}


@router.get("/get.php")
def get_playlist(
    request: Request,
    username: str = Query(...), password: str = Query(...),
    type: str = Query("m3u_plus"),
    output: str = Query("ts"),
    db: Session = Depends(get_db),
):
    user = _authenticate_user(username, password, db)
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
def get_epg_xml(
    username: str = Query(...), password: str = Query(...),
    db: Session = Depends(get_db),
):
    user = _authenticate_user(username, password, db)
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
