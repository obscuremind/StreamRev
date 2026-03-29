"""Web player panel for end-user streaming - live TV, movies, series, profile."""

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.database import get_db
from src.core.auth.password import verify_password
from src.domain.models import User
from src.domain.stream.service import StreamService
from src.domain.category.service import CategoryService
from src.domain.vod.service import MovieService, SeriesService
from src.domain.user.service import UserService

router = APIRouter(prefix="/player", tags=["Web Player"])


def _auth_player(username: str, password: str, db: Session) -> User:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=403, detail="Invalid credentials")
    if not user.enabled:
        raise HTTPException(status_code=403, detail="Account disabled")
    svc = UserService(db)
    if svc.is_expired(user):
        raise HTTPException(status_code=403, detail="Account expired")
    return user


@router.get("/login")
def player_login_page():
    return HTMLResponse(
        content="""<!DOCTYPE html><html><head><title>Player Login</title>
<style>body{font-family:sans-serif;background:#1a1a2e;color:#eee;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}
.card{background:#16213e;padding:2rem;border-radius:12px;width:350px;box-shadow:0 8px 32px rgba(0,0,0,0.3)}
input{width:100%;padding:10px;margin:8px 0;border:1px solid #333;border-radius:8px;background:#0f3460;color:#eee;box-sizing:border-box}
button{width:100%;padding:12px;background:#e94560;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:1rem;margin-top:8px}
h2{text-align:center;color:#e94560}</style></head><body>
<div class="card"><h2>IPTV Player</h2>
<form method="GET" action="/player/home"><input name="username" placeholder="Username" required/>
<input name="password" type="password" placeholder="Password" required/><button type="submit">Login</button></form>
</div></body></html>"""
    )


@router.post("/login")
def player_login_submit(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """XC_VM compatibility POST login route."""
    _auth_player(username, password, db)
    return RedirectResponse(url=f"/player/index?username={username}&password={password}", status_code=302)


@router.get("/home")
def player_home(username: str = Query(...), password: str = Query(...), db: Session = Depends(get_db)):
    user = _auth_player(username, password, db)
    cat_svc = CategoryService(db)
    live_cats = cat_svc.get_live_categories()
    movie_cats = cat_svc.get_movie_categories()
    series_cats = cat_svc.get_series_categories()
    return {
        "user": {
            "username": user.username,
            "exp_date": str(user.exp_date) if user.exp_date else None,
            "max_connections": user.max_connections,
        },
        "live_categories": [{"id": c.id, "name": c.category_name} for c in live_cats],
        "movie_categories": [{"id": c.id, "name": c.category_name} for c in movie_cats],
        "series_categories": [{"id": c.id, "name": c.category_name} for c in series_cats],
    }


@router.get("/index")
def player_index(username: str = Query(...), password: str = Query(...), db: Session = Depends(get_db)):
    """XC_VM compatibility alias for player home/index."""
    return player_home(username=username, password=password, db=db)


@router.get("/live")
def player_live(
    username: str = Query(...),
    password: str = Query(...),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    user = _auth_player(username, password, db)
    svc = StreamService(db)
    streams = svc.get_live_streams(category_id=category_id)
    base = f"{settings.SERVER_PROTOCOL}://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
    return [
        {
            "id": s.id,
            "name": s.stream_display_name,
            "icon": s.stream_icon,
            "category_id": s.category_id,
            "url": f"{base}/live/{username}/{password}/{s.id}.m3u8",
        }
        for s in streams
    ]


@router.get("/movies")
def player_movies(
    username: str = Query(...),
    password: str = Query(...),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    user = _auth_player(username, password, db)
    result = MovieService(db).get_all(category_id=category_id, per_page=500)
    base = f"{settings.SERVER_PROTOCOL}://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
    return [
        {
            "id": m.id,
            "name": m.stream_display_name,
            "icon": m.stream_icon,
            "plot": m.plot,
            "rating": m.rating,
            "genre": m.genre,
            "url": f"{base}/movie/{username}/{password}/{m.id}.{m.container_extension or 'mp4'}",
        }
        for m in result["items"]
    ]


@router.get("/movie")
def player_movie(
    movie_id: int = Query(...),
    username: str = Query(...),
    password: str = Query(...),
    db: Session = Depends(get_db),
):
    """XC_VM compatibility endpoint for single movie details."""
    _auth_player(username, password, db)
    movie = MovieService(db).get_by_id(movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    base = f"{settings.SERVER_PROTOCOL}://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
    return {
        "id": movie.id,
        "name": movie.stream_display_name,
        "icon": movie.stream_icon,
        "plot": movie.plot,
        "rating": movie.rating,
        "genre": movie.genre,
        "url": f"{base}/movie/{username}/{password}/{movie.id}.{movie.container_extension or 'mp4'}",
    }


@router.get("/series")
def player_series(
    username: str = Query(...),
    password: str = Query(...),
    category_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    user = _auth_player(username, password, db)
    result = SeriesService(db).get_all(category_id=category_id, per_page=500)
    return [
        {
            "id": s.id,
            "title": s.title,
            "cover": s.cover,
            "plot": s.plot,
            "genre": s.genre,
            "rating": s.rating,
        }
        for s in result["items"]
    ]


@router.get("/series/{series_id}/episodes")
def player_episodes(
    series_id: int,
    username: str = Query(...),
    password: str = Query(...),
    db: Session = Depends(get_db),
):
    user = _auth_player(username, password, db)
    episodes = SeriesService(db).get_episodes(series_id)
    base = f"{settings.SERVER_PROTOCOL}://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
    return [
        {
            "id": e.id,
            "title": e.stream_display_name,
            "season": e.season_number,
            "episode": e.episode_number,
            "plot": e.plot,
            "duration": e.duration,
            "url": f"{base}/series/{username}/{password}/{e.id}.{e.container_extension or 'mp4'}",
        }
        for e in episodes
    ]


@router.get("/episodes")
def player_episodes_alias(
    series_id: int = Query(...),
    username: str = Query(...),
    password: str = Query(...),
    db: Session = Depends(get_db),
):
    """XC_VM compatibility alias for episode listing endpoint."""
    return player_episodes(series_id=series_id, username=username, password=password, db=db)


@router.get("/profile")
def player_profile(username: str = Query(...), password: str = Query(...), db: Session = Depends(get_db)):
    user = _auth_player(username, password, db)
    svc = UserService(db)
    return {
        "username": user.username,
        "exp_date": str(user.exp_date) if user.exp_date else None,
        "max_connections": user.max_connections,
        "is_trial": user.is_trial,
        "active_connections": svc.get_active_connections(user.id),
        "created_at": str(user.created_at) if user.created_at else None,
    }


@router.get("/listings")
def player_listings(username: str = Query(...), password: str = Query(...), db: Session = Depends(get_db)):
    """XC_VM-compatible listing summary endpoint for player panel."""
    _auth_player(username, password, db)
    return {
        "live": player_live(username=username, password=password, db=db),
        "movies": player_movies(username=username, password=password, db=db),
        "series": player_series(username=username, password=password, db=db),
    }


@router.get("/logout")
def player_logout():
    """XC_VM-compatible logout endpoint for player scope."""
    return {
        "status": "ok",
        "message": "Logged out. Remove client-side cached credentials/session.",
    }


@router.get("/proxy")
def player_proxy(
    target: str = Query(..., description="Absolute media URL"),
    username: str = Query(...),
    password: str = Query(...),
    db: Session = Depends(get_db),
):
    """XC_VM-compatible proxy endpoint using redirect semantics."""
    _auth_player(username, password, db)
    return RedirectResponse(url=target, status_code=307)


@router.get("/resize")
def player_resize(
    username: str = Query(...),
    password: str = Query(...),
    db: Session = Depends(get_db),
):
    """XC_VM compatibility endpoint used by legacy player clients."""
    _auth_player(username, password, db)
    return {"status": "ok", "mode": "resize", "width": 1920, "height": 1080}
