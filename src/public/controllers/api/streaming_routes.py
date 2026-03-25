"""
Streaming routes for live channels, VOD, and series playback.
Supports TS, M3U8, and direct source redirect.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import json
from src.core.database import get_db
from src.streaming.auth.stream_auth import StreamAuth
from src.streaming.engine import streaming_engine
from src.streaming.delivery.hls_handler import hls_handler
from src.streaming.protection.connection_limiter import connection_limiter
from src.domain.models import Stream, Movie, SeriesEpisode
from src.domain.line.service import LineService

router = APIRouter(tags=["Streaming"])


@router.get("/live/{username}/{password}/{stream_id_ext}")
async def live_stream(username: str, password: str, stream_id_ext: str,
                      request: Request, db: Session = Depends(get_db)):
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

    ok, stream, err = auth.authorize_stream(
        user,
        stream_id,
        user_agent=request.headers.get("user-agent"),
        client_ip=client_ip,
    )
    if not ok:
        raise HTTPException(status_code=403, detail=err)

    if not connection_limiter.can_connect(user.id, user.max_connections):
        raise HTTPException(status_code=403, detail="Max connections reached")

    conn_id = f"{user.id}_{stream_id}_{client_ip}"
    connection_limiter.add_connection(user.id, conn_id)

    line_svc = LineService(db)
    line_svc.create_line({
        "user_id": user.id,
        "stream_id": stream_id,
        "server_id": stream.tv_archive_server_id or 1,
        "container": container,
        "user_ip": client_ip,
        "user_agent": request.headers.get("user-agent", ""),
    })

    if stream.direct_source:
        sources = []
        try:
            sources = json.loads(stream.stream_source) if stream.stream_source else []
        except (json.JSONDecodeError, TypeError):
            sources = [stream.stream_source] if stream.stream_source else []
        if sources:
            return RedirectResponse(url=sources[0], status_code=302)
        raise HTTPException(status_code=404, detail="No source available")

    if container == "m3u8":
        playlist = hls_handler.get_playlist(stream_id)
        if playlist:
            return Response(content=playlist, media_type="application/vnd.apple.mpegurl")

        sources = []
        try:
            sources = json.loads(stream.stream_source) if stream.stream_source else []
        except (json.JSONDecodeError, TypeError):
            sources = [stream.stream_source] if stream.stream_source else []
        if sources:
            streaming_engine.start_stream(stream_id, sources[0], container="m3u8")
            return Response(content="#EXTM3U\n#EXT-X-VERSION:3\n", media_type="application/vnd.apple.mpegurl")

    sources = []
    try:
        sources = json.loads(stream.stream_source) if stream.stream_source else []
    except (json.JSONDecodeError, TypeError):
        sources = [stream.stream_source] if stream.stream_source else []
    if sources:
        return RedirectResponse(url=sources[0], status_code=302)

    raise HTTPException(status_code=404, detail="Stream not available")


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


@router.get("/timeshift/{username}/{password}/{duration}/{start}/{stream_id_ext}")
async def timeshift_stream(username: str, password: str, duration: str, start: str,
                           stream_id_ext: str, request: Request, db: Session = Depends(get_db)):
    auth = StreamAuth(db)
    ok, user, err = auth.authenticate(username, password)
    if not ok:
        raise HTTPException(status_code=403, detail=err)
    raise HTTPException(status_code=501, detail="Timeshift not yet implemented")
