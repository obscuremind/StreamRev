"""Generates M3U/M3U8 playlists for various contexts."""

import json
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.models import Bouquet, Movie, Stream, StreamCategory


class PlaylistGenerator:
    def __init__(self, db: Session):
        self.db = db

    def generate_m3u(
        self,
        streams: List[Stream],
        base_url: str,
        username: str,
        password: str,
        output: str = "ts",
        include_vod: bool = True,
    ) -> str:
        categories = {c.id: c.category_name for c in self.db.query(StreamCategory).all()}
        lines = ["#EXTM3U"]
        for s in streams:
            cat_name = categories.get(s.category_id, "Uncategorized")
            tvg_id = s.epg_channel_id or ""
            tvg_logo = s.stream_icon or ""
            lines.append(
                f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{s.stream_display_name}" '
                f'tvg-logo="{tvg_logo}" group-title="{cat_name}",{s.stream_display_name}'
            )
            lines.append(f"{base_url}/live/{username}/{password}/{s.id}.{output}")
        if include_vod:
            movies = self.db.query(Movie).all()
            for m in movies:
                cat_name = categories.get(m.category_id, "VOD")
                ext = m.container_extension or "mp4"
                lines.append(
                    f'#EXTINF:-1 tvg-name="{m.stream_display_name}" '
                    f'tvg-logo="{m.stream_icon or ""}" group-title="{cat_name}",{m.stream_display_name}'
                )
                lines.append(f"{base_url}/movie/{username}/{password}/{m.id}.{ext}")
        return "\n".join(lines)

    def generate_for_bouquet(
        self,
        bouquet: Bouquet,
        base_url: str,
        username: str,
        password: str,
        output: str = "ts",
    ) -> str:
        channel_ids = json.loads(bouquet.bouquet_channels or "[]")
        streams = (
            self.db.query(Stream)
            .filter(Stream.id.in_(channel_ids), Stream.enabled == True)
            .all()
            if channel_ids
            else []
        )
        return self.generate_m3u(streams, base_url, username, password, output, include_vod=False)

    def generate_radio_m3u(self, base_url: str, username: str, password: str) -> str:
        radios = self.db.query(Stream).filter(Stream.stream_type == 4, Stream.enabled == True).all()
        return self.generate_m3u(radios, base_url, username, password, "ts", include_vod=False)


class StreamSorter:
    @staticmethod
    def sort_by_order(streams: List[Stream]) -> List[Stream]:
        return sorted(streams, key=lambda s: (s.order, s.stream_display_name))

    @staticmethod
    def sort_by_name(streams: List[Stream]) -> List[Stream]:
        return sorted(streams, key=lambda s: s.stream_display_name.lower())

    @staticmethod
    def sort_by_category(streams: List[Stream]) -> List[Stream]:
        return sorted(streams, key=lambda s: (s.category_id or 0, s.order, s.id))


class ProfileService:
    PROFILES = {
        "copy": {"video": "copy", "audio": "copy"},
        "h264_720p": {
            "video": "libx264",
            "video_opts": "-preset fast -s 1280x720 -b:v 2500k",
            "audio": "aac",
            "audio_opts": "-b:a 128k",
        },
        "h264_1080p": {
            "video": "libx264",
            "video_opts": "-preset fast -s 1920x1080 -b:v 5000k",
            "audio": "aac",
            "audio_opts": "-b:a 192k",
        },
        "h264_480p": {
            "video": "libx264",
            "video_opts": "-preset fast -s 854x480 -b:v 1200k",
            "audio": "aac",
            "audio_opts": "-b:a 96k",
        },
        "h265_1080p": {
            "video": "libx265",
            "video_opts": "-preset fast -s 1920x1080 -b:v 3000k",
            "audio": "aac",
            "audio_opts": "-b:a 128k",
        },
        "audio_only": {"video": None, "audio": "aac", "audio_opts": "-b:a 128k"},
    }

    @classmethod
    def get_profile(cls, name: str) -> Optional[Dict]:
        return cls.PROFILES.get(name)

    @classmethod
    def get_all_profiles(cls) -> Dict:
        return cls.PROFILES

    @classmethod
    def build_ffmpeg_args(cls, profile_name: str) -> str:
        profile = cls.get_profile(profile_name)
        if not profile:
            return "-c copy"
        args = []
        if profile.get("video"):
            args.append(f"-c:v {profile['video']}")
            if profile.get("video_opts"):
                args.append(profile["video_opts"])
        elif profile.get("video") is None:
            args.append("-vn")
        if profile.get("audio"):
            args.append(f"-c:a {profile['audio']}")
            if profile.get("audio_opts"):
                args.append(profile["audio_opts"])
        return " ".join(args)
