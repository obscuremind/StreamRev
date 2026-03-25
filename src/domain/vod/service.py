"""VOD domain services: movies and series (including episodes)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.models import Movie, Series, SeriesEpisode


class MovieService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(
        self,
        category_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 50,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = self.db.query(Movie)
        if category_id is not None:
            query = query.filter(Movie.category_id == category_id)
        if search:
            query = query.filter(Movie.stream_display_name.ilike(f"%{search.strip()}%"))
        total = query.count()
        items = (
            query.order_by(Movie.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def get_by_id(self, movie_id: int) -> Optional[Movie]:
        return self.db.query(Movie).filter(Movie.id == movie_id).first()

    def create(self, data: Dict[str, Any]) -> Movie:
        movie = Movie(**data)
        self.db.add(movie)
        self.db.commit()
        self.db.refresh(movie)
        return movie

    def update(self, movie_id: int, data: Dict[str, Any]) -> Optional[Movie]:
        movie = self.get_by_id(movie_id)
        if not movie:
            return None
        for key, value in data.items():
            if hasattr(movie, key):
                setattr(movie, key, value)
        self.db.commit()
        self.db.refresh(movie)
        return movie

    def delete(self, movie_id: int) -> bool:
        movie = self.get_by_id(movie_id)
        if not movie:
            return False
        self.db.delete(movie)
        self.db.commit()
        return True

    def get_stats(self) -> Dict[str, int]:
        return {
            "total": self.db.query(func.count(Movie.id)).scalar() or 0,
            "with_category": self.db.query(func.count(Movie.id))
            .filter(Movie.category_id.isnot(None))
            .scalar()
            or 0,
        }


class SeriesService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(
        self,
        category_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 50,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = self.db.query(Series)
        if category_id is not None:
            query = query.filter(Series.category_id == category_id)
        if search:
            query = query.filter(Series.title.ilike(f"%{search.strip()}%"))
        total = query.count()
        items = (
            query.order_by(Series.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def get_by_id(self, series_id: int) -> Optional[Series]:
        return self.db.query(Series).filter(Series.id == series_id).first()

    def create(self, data: Dict[str, Any]) -> Series:
        series = Series(**data)
        self.db.add(series)
        self.db.commit()
        self.db.refresh(series)
        return series

    def update(self, series_id: int, data: Dict[str, Any]) -> Optional[Series]:
        series = self.get_by_id(series_id)
        if not series:
            return None
        for key, value in data.items():
            if hasattr(series, key):
                setattr(series, key, value)
        self.db.commit()
        self.db.refresh(series)
        return series

    def delete(self, series_id: int) -> bool:
        series = self.get_by_id(series_id)
        if not series:
            return False
        self.db.query(SeriesEpisode).filter(SeriesEpisode.series_id == series_id).delete()
        self.db.delete(series)
        self.db.commit()
        return True

    def get_episodes(self, series_id: int) -> List[SeriesEpisode]:
        return (
            self.db.query(SeriesEpisode)
            .filter(SeriesEpisode.series_id == series_id)
            .order_by(
                SeriesEpisode.season_number.asc(),
                SeriesEpisode.episode_number.asc(),
            )
            .all()
        )

    def add_episode(self, data: Dict[str, Any]) -> SeriesEpisode:
        episode = SeriesEpisode(**data)
        self.db.add(episode)
        self.db.commit()
        self.db.refresh(episode)
        return episode

    def update_episode(
        self, episode_id: int, data: Dict[str, Any]
    ) -> Optional[SeriesEpisode]:
        ep = (
            self.db.query(SeriesEpisode)
            .filter(SeriesEpisode.id == episode_id)
            .first()
        )
        if not ep:
            return None
        for key, value in data.items():
            if hasattr(ep, key):
                setattr(ep, key, value)
        self.db.commit()
        self.db.refresh(ep)
        return ep

    def delete_episode(self, episode_id: int) -> bool:
        ep = (
            self.db.query(SeriesEpisode)
            .filter(SeriesEpisode.id == episode_id)
            .first()
        )
        if not ep:
            return False
        self.db.delete(ep)
        self.db.commit()
        return True

    def get_stats(self) -> Dict[str, int]:
        return {
            "total_series": self.db.query(func.count(Series.id)).scalar() or 0,
            "total_episodes": self.db.query(func.count(SeriesEpisode.id)).scalar() or 0,
        }
