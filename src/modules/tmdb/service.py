"""TMDB service with database integration."""
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.core.logging.logger import logger
from src.domain.models import Movie, Series, Setting
from src.modules.tmdb import TMDBClient, TMDB_API_URL, TMDB_IMAGE_URL


def _get_tmdb_api_key(db: Session) -> Optional[str]:
    row = db.query(Setting).filter(Setting.key == "tmdb_api_key").first()
    return row.value if row and row.value else None


class TMDBService:
    def __init__(self, db: Session):
        self.db = db
        api_key = _get_tmdb_api_key(db) or ""
        self.client = TMDBClient(api_key)

    async def search_and_update_movie(self, movie_id: int) -> Optional[Dict[str, Any]]:
        movie = self.db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            return None
        if movie.tmdb_id:
            details = await self.client.get_movie_details(movie.tmdb_id)
        else:
            result = await self.client.search_movie(movie.stream_display_name)
            if not result:
                return None
            details = await self.client.get_movie_details(result["id"])
        if not details:
            return None
        meta = TMDBClient.extract_metadata(details)
        for k in ("tmdb_id", "plot", "cast", "director", "genre", "release_date",
                   "backdrop_path", "youtube_trailer", "episode_run_time"):
            if k in meta:
                setattr(movie, k, meta[k])
        movie.rating = str(meta.get("rating", ""))
        movie.rating_5based = meta.get("rating_5based", 0.0)
        if meta.get("stream_icon"):
            movie.stream_icon = meta["stream_icon"]
        self.db.commit()
        return meta

    async def search_and_update_series(self, series_id: int) -> Optional[Dict[str, Any]]:
        series = self.db.query(Series).filter(Series.id == series_id).first()
        if not series:
            return None
        if series.tmdb_id:
            details = await self.client.get_series_details(series.tmdb_id)
        else:
            result = await self.client.search_series(series.title)
            if not result:
                return None
            details = await self.client.get_series_details(result["id"])
        if not details:
            return None
        meta = TMDBClient.extract_metadata(details)
        for k in ("tmdb_id", "plot", "cast", "director", "genre", "release_date",
                   "backdrop_path", "youtube_trailer"):
            if k in meta:
                setattr(series, k, meta[k])
        series.rating = str(meta.get("rating", ""))
        series.rating_5based = meta.get("rating_5based", 0.0)
        if meta.get("stream_icon"):
            series.cover = meta["stream_icon"]
        self.db.commit()
        return meta

    async def batch_update_movies(self, movie_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        query = self.db.query(Movie)
        if movie_ids:
            query = query.filter(Movie.id.in_(movie_ids))
        movies = query.all()
        updated = failed = 0
        for m in movies:
            try:
                r = await self.search_and_update_movie(m.id)
                updated += 1 if r else 0
                failed += 0 if r else 1
            except Exception:
                failed += 1
        return {"total": len(movies), "updated": updated, "failed": failed}

    async def batch_update_series(self, series_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        query = self.db.query(Series)
        if series_ids:
            query = query.filter(Series.id.in_(series_ids))
        all_s = query.all()
        updated = failed = 0
        for s in all_s:
            try:
                r = await self.search_and_update_series(s.id)
                updated += 1 if r else 0
                failed += 0 if r else 1
            except Exception:
                failed += 1
        return {"total": len(all_s), "updated": updated, "failed": failed}

    async def get_movie_info(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        details = await self.client.get_movie_details(tmdb_id)
        return TMDBClient.extract_metadata(details) if details else None

    async def get_series_info(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        details = await self.client.get_series_details(tmdb_id)
        return TMDBClient.extract_metadata(details) if details else None

    async def get_season_episodes(self, tmdb_id: int, season: int) -> Optional[List[Dict]]:
        import aiohttp
        url = f"{TMDB_API_URL}/tv/{tmdb_id}/season/{season}"
        params = {"api_key": self.client.api_key}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [{
                            "episode_number": ep.get("episode_number"),
                            "name": ep.get("name", ""),
                            "overview": ep.get("overview", ""),
                            "air_date": ep.get("air_date", ""),
                            "still_path": f"{TMDB_IMAGE_URL}/w300{ep['still_path']}" if ep.get("still_path") else "",
                        } for ep in data.get("episodes", [])]
        except Exception as e:
            logger.error(f"TMDB season fetch failed: {e}")
        return None

    async def search(self, query: str, media_type: str = "movie") -> List[Dict[str, Any]]:
        import aiohttp
        endpoint = "search/movie" if media_type == "movie" else "search/tv"
        url = f"{TMDB_API_URL}/{endpoint}"
        params = {"api_key": self.client.api_key, "query": query}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [{
                            "tmdb_id": i.get("id"),
                            "title": i.get("title") or i.get("name", ""),
                            "overview": i.get("overview", ""),
                            "release_date": i.get("release_date") or i.get("first_air_date", ""),
                            "poster_path": f"{TMDB_IMAGE_URL}/w185{i['poster_path']}" if i.get("poster_path") else "",
                            "vote_average": i.get("vote_average", 0),
                        } for i in data.get("results", [])[:20]]
        except Exception as e:
            logger.error(f"TMDB search failed: {e}")
        return []
