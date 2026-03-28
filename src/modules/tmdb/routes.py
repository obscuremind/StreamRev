"""TMDB admin API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.public.controllers.admin.dependencies import get_current_admin
from src.domain.models import User, Setting
from src.modules.tmdb.service import TMDBService

router = APIRouter(prefix="/api/admin/tmdb", tags=["TMDB"])

@router.get("/search")
async def search_tmdb(
    query: str = Query(..., min_length=1),
    type: str = Query("movie", pattern="^(movie|tv)$"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = TMDBService(db)
    results = await svc.search(query, media_type=type)
    return {"results": results, "query": query, "type": type}

@router.post("/update-movie/{movie_id}")
async def update_movie(movie_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = TMDBService(db)
    result = await svc.search_and_update_movie(movie_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Movie not found or TMDB lookup failed")
    return {"status": "updated", "movie_id": movie_id, "metadata": result}

@router.post("/update-series/{series_id}")
async def update_series(series_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = TMDBService(db)
    result = await svc.search_and_update_series(series_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Series not found or TMDB lookup failed")
    return {"status": "updated", "series_id": series_id, "metadata": result}

@router.post("/batch-update-movies")
async def batch_update_movies(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = TMDBService(db)
    result = await svc.batch_update_movies()
    return {"status": "completed", **result}

@router.post("/batch-update-series")
async def batch_update_series(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = TMDBService(db)
    result = await svc.batch_update_series()
    return {"status": "completed", **result}

@router.get("/movie/{tmdb_id}")
async def get_tmdb_movie(tmdb_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = TMDBService(db)
    info = await svc.get_movie_info(tmdb_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Movie not found on TMDB")
    return info

@router.get("/series/{tmdb_id}")
async def get_tmdb_series(tmdb_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = TMDBService(db)
    info = await svc.get_series_info(tmdb_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Series not found on TMDB")
    return info

@router.get("/config")
def get_tmdb_config(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    row = db.query(Setting).filter(Setting.key == "tmdb_api_key").first()
    has_key = bool(row and row.value)
    return {"api_key_set": has_key, "api_key_preview": (row.value[:4] + "****") if has_key else None}

@router.post("/config")
def set_tmdb_config(payload: dict, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    api_key = payload.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    row = db.query(Setting).filter(Setting.key == "tmdb_api_key").first()
    if row:
        row.value = api_key
    else:
        row = Setting(key="tmdb_api_key", value=api_key, value_type="string")
        db.add(row)
    db.commit()
    return {"status": "saved", "api_key_preview": api_key[:4] + "****"}
