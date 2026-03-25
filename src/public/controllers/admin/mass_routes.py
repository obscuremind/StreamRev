"""Mass edit/delete operations for streams, users, lines, MAG, Enigma, movies, series, episodes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any

from src.core.database import get_db
from src.domain.models import User, Stream, Line, Movie, Series, SeriesEpisode
from src.domain.stream.service import StreamService
from src.domain.user.service import UserService
from src.domain.device.mag_service import MagService
from src.domain.device.enigma_service import EnigmaService
from src.domain.vod.service import SeriesService as SeriesSvc

from .dependencies import get_current_admin

router = APIRouter(prefix="/mass", tags=["Admin Mass Operations"])


class MassUpdate(BaseModel):
    ids: List[int]
    updates: Dict[str, Any]


class MassDelete(BaseModel):
    ids: List[int]


# Streams mass operations
@router.post("/streams/update")
def mass_update_streams(
    data: MassUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    count = db.query(Stream).filter(Stream.id.in_(data.ids)).update(
        {k: v for k, v in data.updates.items() if hasattr(Stream, k)},
        synchronize_session="fetch",
    )
    db.commit()
    return {"affected": count}


@router.post("/streams/delete")
def mass_delete_streams(
    data: MassDelete, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return {"affected": StreamService(db).batch_delete(data.ids)}


# Users mass operations
@router.post("/users/update")
def mass_update_users(
    data: MassUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    updates = {k: v for k, v in data.updates.items() if hasattr(User, k) and k != "password"}
    count = db.query(User).filter(User.id.in_(data.ids)).update(updates, synchronize_session="fetch")
    db.commit()
    return {"affected": count}


@router.post("/users/delete")
def mass_delete_users(
    data: MassDelete, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return {"affected": UserService(db).batch_delete(data.ids)}


# Lines mass operations
@router.post("/lines/delete")
def mass_delete_lines(
    data: MassDelete, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    count = db.query(Line).filter(Line.id.in_(data.ids)).delete(synchronize_session="fetch")
    db.commit()
    return {"affected": count}


# MAG mass operations
@router.post("/mags/update")
def mass_update_mags(
    data: MassUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return {"affected": MagService(db).mass_update(data.ids, data.updates)}


@router.post("/mags/delete")
def mass_delete_mags(
    data: MassDelete, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return {"affected": MagService(db).mass_delete(data.ids)}


# Enigma mass operations
@router.post("/enigmas/update")
def mass_update_enigmas(
    data: MassUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return {"affected": EnigmaService(db).mass_update(data.ids, data.updates)}


@router.post("/enigmas/delete")
def mass_delete_enigmas(
    data: MassDelete, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return {"affected": EnigmaService(db).mass_delete(data.ids)}


# Movies mass operations
@router.post("/movies/update")
def mass_update_movies(
    data: MassUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    updates = {k: v for k, v in data.updates.items() if hasattr(Movie, k)}
    count = db.query(Movie).filter(Movie.id.in_(data.ids)).update(updates, synchronize_session="fetch")
    db.commit()
    return {"affected": count}


@router.post("/movies/delete")
def mass_delete_movies(
    data: MassDelete, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    count = db.query(Movie).filter(Movie.id.in_(data.ids)).delete(synchronize_session="fetch")
    db.commit()
    return {"affected": count}


# Series mass operations
@router.post("/series/delete")
def mass_delete_series(
    data: MassDelete, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    for sid in data.ids:
        SeriesSvc(db).delete(sid)
    return {"affected": len(data.ids)}


# Episodes mass operations
@router.post("/episodes/update")
def mass_update_episodes(
    data: MassUpdate, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    updates = {k: v for k, v in data.updates.items() if hasattr(SeriesEpisode, k)}
    count = (
        db.query(SeriesEpisode)
        .filter(SeriesEpisode.id.in_(data.ids))
        .update(updates, synchronize_session="fetch")
    )
    db.commit()
    return {"affected": count}


@router.post("/episodes/delete")
def mass_delete_episodes(
    data: MassDelete, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    count = (
        db.query(SeriesEpisode).filter(SeriesEpisode.id.in_(data.ids)).delete(synchronize_session="fetch")
    )
    db.commit()
    return {"affected": count}
