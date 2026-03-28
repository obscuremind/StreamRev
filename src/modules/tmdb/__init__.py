"""TMDB metadata integration module."""
import os
from typing import Optional, Dict, Any
from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger

TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p"


class TMDBClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search_movie(self, title: str) -> Optional[Dict[str, Any]]:
        import aiohttp
        url = f"{TMDB_API_URL}/search/movie"
        params = {"api_key": self.api_key, "query": title}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        return results[0] if results else None
        except Exception as e:
            logger.error(f"TMDB search failed: {e}")
        return None

    async def get_movie_details(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        import aiohttp
        url = f"{TMDB_API_URL}/movie/{tmdb_id}"
        params = {"api_key": self.api_key, "append_to_response": "credits,videos"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"TMDB movie details failed: {e}")
        return None

    async def search_series(self, title: str) -> Optional[Dict[str, Any]]:
        import aiohttp
        url = f"{TMDB_API_URL}/search/tv"
        params = {"api_key": self.api_key, "query": title}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        return results[0] if results else None
        except Exception as e:
            logger.error(f"TMDB series search failed: {e}")
        return None

    async def get_series_details(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        import aiohttp
        url = f"{TMDB_API_URL}/tv/{tmdb_id}"
        params = {"api_key": self.api_key, "append_to_response": "credits,videos"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"TMDB series details failed: {e}")
        return None

    @staticmethod
    def extract_metadata(tmdb_data: Dict[str, Any]) -> Dict[str, Any]:
        credits = tmdb_data.get("credits", {})
        cast_list = credits.get("cast", [])[:10]
        crew = credits.get("crew", [])
        directors = [c["name"] for c in crew if c.get("job") == "Director"]
        videos = tmdb_data.get("videos", {}).get("results", [])
        trailers = [v for v in videos if v.get("type") == "Trailer" and v.get("site") == "YouTube"]
        genres = [g["name"] for g in tmdb_data.get("genres", [])]
        return {
            "tmdb_id": tmdb_data.get("id"),
            "plot": tmdb_data.get("overview", ""),
            "cast": ", ".join(c["name"] for c in cast_list),
            "director": ", ".join(directors),
            "genre": ", ".join(genres),
            "release_date": tmdb_data.get("release_date") or tmdb_data.get("first_air_date", ""),
            "rating": tmdb_data.get("vote_average", 0),
            "rating_5based": round((tmdb_data.get("vote_average", 0) or 0) / 2, 1),
            "backdrop_path": f"{TMDB_IMAGE_URL}/w780{tmdb_data['backdrop_path']}" if tmdb_data.get("backdrop_path") else "",
            "stream_icon": f"{TMDB_IMAGE_URL}/w342{tmdb_data['poster_path']}" if tmdb_data.get("poster_path") else "",
            "youtube_trailer": f"https://www.youtube.com/watch?v={trailers[0]['key']}" if trailers else "",
            "episode_run_time": tmdb_data.get("runtime") or (tmdb_data.get("episode_run_time", [0]) or [0])[0],
        }


class Module(ModuleInterface):
    def get_name(self) -> str:
        return "tmdb"

    def get_version(self) -> str:
        return "1.0.0"

    def boot(self, app: Any = None) -> None:
        from src.modules.tmdb.routes import router
        if app is not None:
            app.include_router(router)
        logger.info("TMDB module loaded")

    def get_event_subscribers(self) -> dict:
        return {
            "movie.created": self.on_movie_created,
            "series.created": self.on_series_created,
        }

    async def on_movie_created(self, data):
        from src.core.database import SessionLocal
        from src.modules.tmdb.service import TMDBService
        movie_id = data.get("movie_id") if isinstance(data, dict) else None
        if not movie_id:
            return
        db = SessionLocal()
        try:
            svc = TMDBService(db)
            await svc.search_and_update_movie(movie_id)
        except Exception as e:
            logger.error(f"TMDB auto-update movie failed: {e}")
        finally:
            db.close()

    async def on_series_created(self, data):
        from src.core.database import SessionLocal
        from src.modules.tmdb.service import TMDBService
        series_id = data.get("series_id") if isinstance(data, dict) else None
        if not series_id:
            return
        db = SessionLocal()
        try:
            svc = TMDBService(db)
            await svc.search_and_update_series(series_id)
        except Exception as e:
            logger.error(f"TMDB auto-update series failed: {e}")
        finally:
            db.close()
