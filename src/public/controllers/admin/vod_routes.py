from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, Optional

from src.core.database import get_db
from src.domain.models import SeriesEpisode, User
from src.domain.vod.service import MovieService, SeriesService
from .dependencies import get_current_admin

router = APIRouter(prefix="/vod", tags=["Admin VOD"])


# --- Movies ---


class MovieCreate(BaseModel):
    stream_display_name: str
    stream_source: str = ""
    stream_icon: Optional[str] = None
    rating: Optional[str] = None
    rating_5based: Optional[float] = None
    category_id: Optional[int] = None
    container_extension: str = "mkv"
    custom_sid: Optional[str] = None
    direct_source: bool = False
    target_container: str = "ts"
    tmdb_id: Optional[int] = None
    plot: Optional[str] = None
    cast: Optional[str] = None
    director: Optional[str] = None
    genre: Optional[str] = None
    release_date: Optional[str] = None
    episode_run_time: Optional[int] = None
    youtube_trailer: Optional[str] = None
    backdrop_path: Optional[str] = None


class MovieUpdate(BaseModel):
    stream_display_name: Optional[str] = None
    stream_source: Optional[str] = None
    stream_icon: Optional[str] = None
    rating: Optional[str] = None
    rating_5based: Optional[float] = None
    category_id: Optional[int] = None
    container_extension: Optional[str] = None
    custom_sid: Optional[str] = None
    direct_source: Optional[bool] = None
    target_container: Optional[str] = None
    tmdb_id: Optional[int] = None
    plot: Optional[str] = None
    cast: Optional[str] = None
    director: Optional[str] = None
    genre: Optional[str] = None
    release_date: Optional[str] = None
    episode_run_time: Optional[int] = None
    youtube_trailer: Optional[str] = None
    backdrop_path: Optional[str] = None


@router.get("/movies")
def list_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = MovieService(db)
    result = svc.get_all(
        category_id=category_id, page=page, per_page=per_page, search=search
    )
    result["items"] = [_movie_to_dict(m) for m in result["items"]]
    return result


@router.get("/movies/stats")
def movie_stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return MovieService(db).get_stats()


@router.get("/movies/{movie_id}")
def get_movie(
    movie_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    m = MovieService(db).get_by_id(movie_id)
    if not m:
        raise HTTPException(status_code=404, detail="Movie not found")
    return _movie_to_dict(m)


@router.post("/movies")
def create_movie(
    data: MovieCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return _movie_to_dict(MovieService(db).create(data.model_dump(exclude_none=True)))


@router.put("/movies/{movie_id}")
def update_movie(
    movie_id: int,
    data: MovieUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    m = MovieService(db).update(movie_id, data.model_dump(exclude_none=True))
    if not m:
        raise HTTPException(status_code=404, detail="Movie not found")
    return _movie_to_dict(m)


@router.delete("/movies/{movie_id}")
def delete_movie(
    movie_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not MovieService(db).delete(movie_id):
        raise HTTPException(status_code=404, detail="Movie not found")
    return {"status": "deleted"}


def _movie_to_dict(m) -> dict[str, Any]:
    return {
        "id": m.id,
        "stream_display_name": m.stream_display_name,
        "stream_source": m.stream_source,
        "stream_icon": m.stream_icon,
        "rating": m.rating,
        "rating_5based": m.rating_5based,
        "category_id": m.category_id,
        "container_extension": m.container_extension,
        "custom_sid": m.custom_sid,
        "added": str(m.added) if m.added else None,
        "direct_source": m.direct_source,
        "target_container": m.target_container,
        "tmdb_id": m.tmdb_id,
        "plot": m.plot,
        "cast": m.cast,
        "director": m.director,
        "genre": m.genre,
        "release_date": m.release_date,
        "episode_run_time": m.episode_run_time,
        "youtube_trailer": m.youtube_trailer,
        "backdrop_path": m.backdrop_path,
    }


# --- Series ---


class SeriesCreate(BaseModel):
    title: str
    category_id: Optional[int] = None
    cover: Optional[str] = None
    plot: Optional[str] = None
    cast: Optional[str] = None
    director: Optional[str] = None
    genre: Optional[str] = None
    release_date: Optional[str] = None
    rating: Optional[str] = None
    rating_5based: Optional[float] = None
    backdrop_path: Optional[str] = None
    youtube_trailer: Optional[str] = None
    tmdb_id: Optional[int] = None


class SeriesUpdate(BaseModel):
    title: Optional[str] = None
    category_id: Optional[int] = None
    cover: Optional[str] = None
    plot: Optional[str] = None
    cast: Optional[str] = None
    director: Optional[str] = None
    genre: Optional[str] = None
    release_date: Optional[str] = None
    rating: Optional[str] = None
    rating_5based: Optional[float] = None
    backdrop_path: Optional[str] = None
    youtube_trailer: Optional[str] = None
    tmdb_id: Optional[int] = None


@router.get("/series")
def list_series(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SeriesService(db)
    result = svc.get_all(
        category_id=category_id, page=page, per_page=per_page, search=search
    )
    result["items"] = [_series_to_dict(s) for s in result["items"]]
    return result


@router.get("/series/stats")
def series_stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return SeriesService(db).get_stats()


@router.get("/series/{series_id}")
def get_series(
    series_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    s = SeriesService(db).get_by_id(series_id)
    if not s:
        raise HTTPException(status_code=404, detail="Series not found")
    return _series_to_dict(s)


@router.post("/series")
def create_series(
    data: SeriesCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return _series_to_dict(SeriesService(db).create(data.model_dump(exclude_none=True)))


@router.put("/series/{series_id}")
def update_series(
    series_id: int,
    data: SeriesUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    s = SeriesService(db).update(series_id, data.model_dump(exclude_none=True))
    if not s:
        raise HTTPException(status_code=404, detail="Series not found")
    return _series_to_dict(s)


@router.delete("/series/{series_id}")
def delete_series(
    series_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not SeriesService(db).delete(series_id):
        raise HTTPException(status_code=404, detail="Series not found")
    return {"status": "deleted"}


def _series_to_dict(s) -> dict[str, Any]:
    return {
        "id": s.id,
        "title": s.title,
        "category_id": s.category_id,
        "cover": s.cover,
        "plot": s.plot,
        "cast": s.cast,
        "director": s.director,
        "genre": s.genre,
        "release_date": s.release_date,
        "rating": s.rating,
        "rating_5based": s.rating_5based,
        "backdrop_path": s.backdrop_path,
        "youtube_trailer": s.youtube_trailer,
        "tmdb_id": s.tmdb_id,
        "last_modified": str(s.last_modified) if s.last_modified else None,
    }


# --- Episodes ---


class EpisodeCreate(BaseModel):
    season_number: int = 1
    episode_number: int = 1
    stream_display_name: str = ""
    stream_source: str = ""
    container_extension: str = "mkv"
    custom_sid: Optional[str] = None
    direct_source: bool = False
    tmdb_id: Optional[int] = None
    plot: Optional[str] = None
    duration: Optional[int] = None
    rating: Optional[str] = None
    movie_image: Optional[str] = None
    bitrate: Optional[int] = None


class EpisodeUpdate(BaseModel):
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    stream_display_name: Optional[str] = None
    stream_source: Optional[str] = None
    container_extension: Optional[str] = None
    custom_sid: Optional[str] = None
    direct_source: Optional[bool] = None
    tmdb_id: Optional[int] = None
    plot: Optional[str] = None
    duration: Optional[int] = None
    rating: Optional[str] = None
    movie_image: Optional[str] = None
    bitrate: Optional[int] = None


@router.get("/series/{series_id}/episodes")
def list_episodes(
    series_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SeriesService(db)
    if not svc.get_by_id(series_id):
        raise HTTPException(status_code=404, detail="Series not found")
    return [_episode_to_dict(e) for e in svc.get_episodes(series_id)]


@router.post("/series/{series_id}/episodes")
def create_episode(
    series_id: int,
    data: EpisodeCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SeriesService(db)
    if not svc.get_by_id(series_id):
        raise HTTPException(status_code=404, detail="Series not found")
    payload = data.model_dump(exclude_none=True)
    payload["series_id"] = series_id
    return _episode_to_dict(svc.add_episode(payload))


@router.get("/series/{series_id}/episodes/{episode_id}")
def get_episode(
    series_id: int,
    episode_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SeriesService(db)
    if not svc.get_by_id(series_id):
        raise HTTPException(status_code=404, detail="Series not found")
    eps = {e.id: e for e in svc.get_episodes(series_id)}
    ep = eps.get(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return _episode_to_dict(ep)


@router.put("/series/{series_id}/episodes/{episode_id}")
def update_episode(
    series_id: int,
    episode_id: int,
    data: EpisodeUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SeriesService(db)
    if not svc.get_by_id(series_id):
        raise HTTPException(status_code=404, detail="Series not found")
    ep = svc.update_episode(episode_id, data.model_dump(exclude_none=True))
    if not ep or ep.series_id != series_id:
        raise HTTPException(status_code=404, detail="Episode not found")
    return _episode_to_dict(ep)


@router.delete("/series/{series_id}/episodes/{episode_id}")
def delete_episode(
    series_id: int,
    episode_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = SeriesService(db)
    if not svc.get_by_id(series_id):
        raise HTTPException(status_code=404, detail="Series not found")
    ep = (
        db.query(SeriesEpisode)
        .filter(
            SeriesEpisode.id == episode_id,
            SeriesEpisode.series_id == series_id,
        )
        .first()
    )
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    if not svc.delete_episode(episode_id):
        raise HTTPException(status_code=404, detail="Episode not found")
    return {"status": "deleted"}


def _episode_to_dict(e) -> dict[str, Any]:
    return {
        "id": e.id,
        "series_id": e.series_id,
        "season_number": e.season_number,
        "episode_number": e.episode_number,
        "stream_display_name": e.stream_display_name,
        "stream_source": e.stream_source,
        "container_extension": e.container_extension,
        "custom_sid": e.custom_sid,
        "added": str(e.added) if e.added else None,
        "direct_source": e.direct_source,
        "tmdb_id": e.tmdb_id,
        "plot": e.plot,
        "duration": e.duration,
        "rating": e.rating,
        "movie_image": e.movie_image,
        "bitrate": e.bitrate,
    }
