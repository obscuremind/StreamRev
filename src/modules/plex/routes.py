"""Plex integration API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.public.controllers.admin.dependencies import get_current_admin
from src.domain.models import User, Stream, Movie, Series
from src.modules.plex.service import PlexService

router = APIRouter(tags=["Plex"])

@router.get("/api/plex/playlist.m3u")
def plex_playlist(username: str = Query(...), password: str = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username, User.password == password, User.enabled == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    svc = PlexService(db)
    m3u = svc.generate_m3u(user.id)
    if m3u is None:
        raise HTTPException(status_code=404, detail="Playlist generation failed")
    return Response(content=m3u, media_type="audio/x-mpegurl", headers={"Content-Disposition": "attachment; filename=playlist.m3u"})

@router.get("/api/plex/xmltv.xml")
def plex_xmltv(username: str = Query(...), password: str = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username, User.password == password, User.enabled == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    svc = PlexService(db)
    xmltv = svc.generate_xmltv(user.id)
    if xmltv is None:
        raise HTTPException(status_code=404, detail="EPG generation failed")
    return Response(content=xmltv, media_type="application/xml", headers={"Content-Disposition": "attachment; filename=xmltv.xml"})

@router.get("/api/plex/library/sections")
def plex_library_sections(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = PlexService(db)
    return {"sections": svc.get_library_sections()}

@router.get("/api/plex/library/sections/{section_id}/all")
def plex_section_items(section_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = PlexService(db)
    items = svc.get_section_items(section_id)
    return {"items": items, "section_id": section_id, "total": len(items)}

@router.get("/api/admin/plex/status")
def plex_status(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    live = db.query(Stream).filter(Stream.enabled == True, Stream.stream_type == 1).count()
    movies = db.query(Movie).count()
    series = db.query(Series).count()
    users = db.query(User).filter(User.enabled == True).count()
    return {"module": "plex", "status": "active", "live_channels": live, "movies": movies, "series": series, "active_users": users}
