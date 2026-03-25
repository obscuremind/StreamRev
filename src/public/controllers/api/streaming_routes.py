"""
Streaming routes for live channels, VOD, and series playback.
Supports TS, M3U8, and direct source redirect.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.domain.line.service import LineService
from src.domain.models import Movie, SeriesEpisode, Server, ServerStream, Stream
from src.domain.server.service import ServerService
from src.streaming.auth.stream_auth import StreamAuth
from src.streaming.balancer.proxy_selector import ProxySelector
from src.streaming.delivery.hls_handler import hls_handler
from src.streaming.engine import streaming_engine
from src.streaming.protection.connection_limiter import connection_limiter

router = APIRouter(tags=["Streaming"])


def _live_sources(stream: Stream) -> list:
    try:
        return json.loads(stream.stream_source) if stream.stream_source else []
    except (json.JSONDecodeError, TypeError):
        return [stream.stream_source] if stream.stream_source else []


def _stream_on_local_server(db: Session, stream_id: int) -> bool:
    main = ServerService(db).get_main_server()
    if not main:
        return True
    ss = (
        db.query(ServerStream)
        .filter(
            ServerStream.server_id == main.id,
            ServerStream.stream_id == stream_id,
        )
        .first()
    )
    return ss is not None


@router.get("/live/{username}/{password}/{stream_id_ext}")
async def live_stream(
    username: str,
    password: str,
    stream_id_ext: str,
    request: Request,
    db: Session = Depends(get_db),
):
    parts = stream_id_ext.rsplit(".", 1)
    stream_id = int(parts[0])
    container = parts[1] if len(parts) > 1 else "ts"

    auth = StreamAuth(db)
    ok, user, err = auth.authenticate(username, password)
    if not ok:
        raise HTTPException(status_code=403, detail=err)

    client_ip = request.client.host if request.client else "unknown"
    if not auth.check_ip_allowed(user, client_ip):
        raise HTTPException(status_code=403, detail="IP not allowed")

    user_agent = request.headers.get("user-agent") or ""
    ok, stream, err = auth.authorize_stream(
        user,
        stream_id,
        user_agent=user_agent,
        client_ip=client_ip,
    )
    if not ok:
        raise HTTPException(status_code=403, detail=err)

    if not connection_limiter.can_connect(user.id, user.max_connections):
        raise HTTPException(status_code=403, detail="Max connections reached")

    conn_id = f"{user.id}_{stream_id}_{client_ip}"
    connection_limiter.add_connection(user.id, conn_id)

    line_svc = LineService(db)
    line = None
    try:
        line = line_svc.create_line(
            {
                "user_id": user.id,
                "stream_id": stream_id,
                "server_id": stream.tv_archive_server_id or 1,
                "container": container,
                "user_ip": client_ip,
                "user_agent": user_agent,
            }
        )
        if stream.direct_source:
            sources = _live_sources(stream)
            if sources:
                return RedirectResponse(url=sources[0], status_code=302)
            raise HTTPException(status_code=404, detail="No source available")

        if not _stream_on_local_server(db, stream_id):
            main = ServerService(db).get_main_server()
            proxy = ProxySelector(db)
            best = proxy.select_server(
                stream_id,
                exclude_server_id=main.id if main else None,
            )
            if best:
                url = proxy.get_player_live_url(
                    best, username, password, stream_id, container
                )
                return RedirectResponse(url=url, status_code=302)
            raise HTTPException(
                status_code=503,
                detail="No edge server available for this stream",
            )

        if container == "m3u8":
            playlist = hls_handler.get_playlist(stream_id)
            if playlist:
                return Response(
                    content=playlist, media_type="application/vnd.apple.mpegurl"
                )

            sources = _live_sources(stream)
            if sources:
                streaming_engine.start_stream(
                    stream_id, sources[0], container="m3u8"
                )
                return Response(
                    content="#EXTM3U\n#EXT-X-VERSION:3\n",
                    media_type="application/vnd.apple.mpegurl",
                )

        sources = _live_sources(stream)
        if sources:
            return RedirectResponse(url=sources[0], status_code=302)

        raise HTTPException(status_code=404, detail="Stream not available")
    finally:
        connection_limiter.remove_connection(user.id, conn_id)
        if line is not None:
            line_svc.remove_line(line.id)


@router.get("/movie/{username}/{password}/{movie_id_ext}")
async def vod_stream(username: str, password: str, movie_id_ext: str,
                     request: Request, db: Session = Depends(get_db)):
    parts = movie_id_ext.rsplit(".", 1)
    movie_id = int(parts[0])

    auth = StreamAuth(db)
    ok, user, err = auth.authenticate(username, password)
    if not ok:
        raise HTTPException(status_code=403, detail=err)

    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    if movie.direct_source and movie.stream_source:
        return RedirectResponse(url=movie.stream_source, status_code=302)

    if movie.stream_source:
        return RedirectResponse(url=movie.stream_source, status_code=302)

    raise HTTPException(status_code=404, detail="VOD not available")


@router.get("/series/{username}/{password}/{episode_id_ext}")
async def series_stream(username: str, password: str, episode_id_ext: str,
                        request: Request, db: Session = Depends(get_db)):
    parts = episode_id_ext.rsplit(".", 1)
    episode_id = int(parts[0])

    auth = StreamAuth(db)
    ok, user, err = auth.authenticate(username, password)
    if not ok:
        raise HTTPException(status_code=403, detail=err)

    episode = db.query(SeriesEpisode).filter(SeriesEpisode.id == episode_id).first()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    if episode.direct_source and episode.stream_source:
        return RedirectResponse(url=episode.stream_source, status_code=302)

    if episode.stream_source:
        return RedirectResponse(url=episode.stream_source, status_code=302)

    raise HTTPException(status_code=404, detail="Episode not available")


@router.get("/hls/{stream_id}/index.m3u8")
async def hls_playlist(stream_id: int):
    playlist = hls_handler.get_playlist(stream_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return Response(content=playlist, media_type="application/vnd.apple.mpegurl")


@router.get("/hls/{stream_id}/{segment}")
async def hls_segment(stream_id: int, segment: str):
    data = hls_handler.get_segment(stream_id, segment)
    if not data:
        raise HTTPException(status_code=404, detail="Segment not found")
    return Response(content=data, media_type="video/mp2t")


def _parse_timeshift_start(raw: str) -> datetime:
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="Missing start time")
    if s.isdigit():
        return datetime.fromtimestamp(int(s), tz=timezone.utc).replace(tzinfo=None)
    for fmt in ("%Y%m%d%H%M%S", "%Y-%m-%d:%H-%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise HTTPException(status_code=400, detail="Invalid start time format")


def _parse_timeshift_duration(raw: str) -> int:
    s = (raw or "").strip()
    if not s or not s.isdigit():
        raise HTTPException(status_code=400, detail="Invalid duration")
    return int(s)


@router.get("/timeshift/{username}/{password}/{duration}/{start}/{stream_id_ext}")
async def timeshift_stream(
    username: str,
    password: str,
    duration: str,
    start: str,
    stream_id_ext: str,
    request: Request,
    db: Session = Depends(get_db),
):
    auth = StreamAuth(db)
    ok, user, err = auth.authenticate(username, password)
    if not ok:
        raise HTTPException(status_code=403, detail=err)

    client_ip = request.client.host if request.client else "unknown"
    if not auth.check_ip_allowed(user, client_ip):
        raise HTTPException(status_code=403, detail="IP not allowed")

    user_agent = request.headers.get("user-agent") or ""

    parts = stream_id_ext.rsplit(".", 1)
    stream_id = int(parts[0])

    ok, stream, err = auth.authorize_stream(
        user,
        stream_id,
        user_agent=user_agent,
        client_ip=client_ip,
    )
    if not ok:
        raise HTTPException(status_code=403, detail=err)

    if not stream.tv_archive:
        raise HTTPException(status_code=403, detail="TV archive disabled for this channel")

    start_dt = _parse_timeshift_start(start)
    duration_sec = _parse_timeshift_duration(duration)

    if stream.tv_archive_duration and stream.tv_archive_duration > 0:
        oldest = datetime.utcnow() - timedelta(days=stream.tv_archive_duration)
        if start_dt < oldest:
            raise HTTPException(status_code=403, detail="Start time outside archive window")

    date_dir = start_dt.strftime("%Y-%m-%d")
    archive_dir = os.path.join(
        settings.CONTENT_DIR, "archive", str(stream_id), date_dir
    )

    archive_server: Server | None = None
    if stream.tv_archive_server_id:
        archive_server = (
            db.query(Server)
            .filter(Server.id == stream.tv_archive_server_id)
            .first()
        )

    main = ServerService(db).get_main_server()
    use_remote = (
        archive_server is not None
        and main is not None
        and archive_server.id != main.id
    )

    if use_remote:
        protocol = archive_server.server_protocol or "http"
        port = (
            archive_server.https_port
            if protocol == "https"
            else archive_server.http_port
        )
        host = (archive_server.domain_name or "").strip() or archive_server.server_ip
        base = (archive_server.timeshift_path or "").strip().rstrip("/")
        if base:
            dest = (
                f"{base}/timeshift/{username}/{password}/"
                f"{duration}/{start}/{stream_id_ext}"
            )
        else:
            dest = (
                f"{protocol}://{host}:{port}/timeshift/"
                f"{username}/{password}/{duration}/{start}/{stream_id_ext}"
            )
        return RedirectResponse(url=dest, status_code=302)

    if os.path.isdir(archive_dir):
        for name in ("index.m3u8", "playlist.m3u8", "archive.m3u8"):
            path = os.path.join(archive_dir, name)
            if os.path.isfile(path):
                return FileResponse(
                    path, media_type="application/vnd.apple.mpegurl"
                )
        rel_base = f"/static/archive/{stream_id}/{date_dir}"
        playlist_url = (
            f"{rel_base}/index.m3u8?duration={duration_sec}&start={start}"
        )
        return RedirectResponse(url=playlist_url, status_code=302)

    archive_url = (
        f"{request.url.scheme}://{request.url.netloc}"
        f"/content/archive/{stream_id}/{date_dir}/"
        f"index.m3u8?duration={duration_sec}&start={start}"
    )
    return RedirectResponse(url=archive_url, status_code=302)
