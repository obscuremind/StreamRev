"""Plex-compatible M3U, XMLTV, and library section generation."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.core.config import settings
from src.core.logging.logger import logger
from src.domain.models import User, Stream, StreamCategory, Movie, Series, EpgData, Bouquet


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class PlexService:
    def __init__(self, db: Session):
        self.db = db

    def _get_user(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id, User.enabled == True).first()

    def _get_streams_for_user(self, user: User) -> List[Stream]:
        query = self.db.query(Stream).filter(Stream.enabled == True, Stream.stream_type == 1)
        if user.bouquet:
            try:
                bids = [int(b) for b in user.bouquet.split(",") if b.strip()]
                if bids:
                    bouquets = self.db.query(Bouquet).filter(Bouquet.id.in_(bids)).all()
                    allowed = set()
                    for bq in bouquets:
                        try:
                            allowed.update(int(i) for i in json.loads(bq.bouquet_channels))
                        except (json.JSONDecodeError, ValueError):
                            pass
                    if allowed:
                        query = query.filter(Stream.id.in_(allowed))
            except (ValueError, AttributeError):
                pass
        return query.all()

    def _get_movies_for_user(self, user: User) -> List[Movie]:
        query = self.db.query(Movie)
        if user.bouquet:
            try:
                bids = [int(b) for b in user.bouquet.split(",") if b.strip()]
                if bids:
                    bouquets = self.db.query(Bouquet).filter(Bouquet.id.in_(bids)).all()
                    allowed = set()
                    for bq in bouquets:
                        try:
                            allowed.update(int(i) for i in json.loads(bq.bouquet_movies))
                        except (json.JSONDecodeError, ValueError):
                            pass
                    if allowed:
                        query = query.filter(Movie.id.in_(allowed))
            except (ValueError, AttributeError):
                pass
        return query.all()

    def _build_stream_url(self, user: User, stream: Stream) -> str:
        base = f"{settings.SERVER_PROTOCOL}://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
        return f"{base}/{user.username}/{user.password}/{stream.id}"

    def _build_movie_url(self, user: User, movie: Movie) -> str:
        base = f"{settings.SERVER_PROTOCOL}://{settings.SERVER_HOST}:{settings.SERVER_PORT}"
        return f"{base}/movie/{user.username}/{user.password}/{movie.id}.{movie.container_extension}"

    def generate_m3u(self, user_id: int) -> Optional[str]:
        user = self._get_user(user_id)
        if not user:
            return None
        lines = ["#EXTM3U"]
        for s in self._get_streams_for_user(user):
            cat = s.category.category_name if s.category else "Uncategorized"
            tvg_id = s.epg_channel_id or ""
            logo = s.stream_icon or ""
            lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{s.stream_display_name}" tvg-logo="{logo}" group-title="{cat}",{s.stream_display_name}')
            lines.append(self._build_stream_url(user, s))
        for m in self._get_movies_for_user(user):
            cat = m.category.category_name if m.category else "Movies"
            logo = m.stream_icon or ""
            lines.append(f'#EXTINF:-1 tvg-name="{m.stream_display_name}" tvg-logo="{logo}" group-title="{cat}",{m.stream_display_name}')
            lines.append(self._build_movie_url(user, m))
        return "\n".join(lines)

    def generate_xmltv(self, user_id: int) -> Optional[str]:
        user = self._get_user(user_id)
        if not user:
            return None
        streams = self._get_streams_for_user(user)
        parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<tv generator-info-name="StreamRev">']
        for s in streams:
            if s.epg_channel_id:
                parts.append(f'  <channel id="{_xml_escape(s.epg_channel_id)}"><display-name>{_xml_escape(s.stream_display_name)}</display-name></channel>')
        epg = self.db.query(EpgData).filter(
            EpgData.channel_id.in_([s.id for s in streams]),
            EpgData.end >= datetime.utcnow()
        ).all()
        sid_map = {s.id: (s.epg_channel_id or "") for s in streams}
        for ep in epg:
            chan = sid_map.get(ep.channel_id, "")
            if not chan:
                continue
            start = ep.start.strftime("%Y%m%d%H%M%S +0000")
            end = ep.end.strftime("%Y%m%d%H%M%S +0000")
            parts.append(f'  <programme start="{start}" stop="{end}" channel="{_xml_escape(chan)}"><title>{_xml_escape(ep.title)}</title><desc>{_xml_escape(ep.description or "")}</desc></programme>')
        parts.append("</tv>")
        return "\n".join(parts)

    def get_library_sections(self) -> List[Dict[str, Any]]:
        live = self.db.query(Stream).filter(Stream.enabled == True, Stream.stream_type == 1).count()
        movies = self.db.query(Movie).count()
        series = self.db.query(Series).count()
        return [
            {"id": 1, "title": "Live TV", "type": "show", "count": live},
            {"id": 2, "title": "Movies", "type": "movie", "count": movies},
            {"id": 3, "title": "TV Series", "type": "show", "count": series},
        ]

    def get_section_items(self, section_id: int) -> List[Dict[str, Any]]:
        if section_id == 1:
            return [{"id": s.id, "title": s.stream_display_name, "type": "channel", "icon": s.stream_icon or ""} for s in self.db.query(Stream).filter(Stream.enabled == True, Stream.stream_type == 1).all()]
        elif section_id == 2:
            return [{"id": m.id, "title": m.stream_display_name, "type": "movie", "icon": m.stream_icon or "", "year": (m.release_date or "")[:4]} for m in self.db.query(Movie).all()]
        elif section_id == 3:
            return [{"id": s.id, "title": s.title, "type": "series", "icon": s.cover or ""} for s in self.db.query(Series).all()]
        return []
