import os
from typing import Optional
from src.core.config import settings


class HLSHandler:
    def __init__(self):
        self.streams_dir = os.path.join(settings.CONTENT_DIR, "streams")

    def get_playlist(self, stream_id: int) -> Optional[str]:
        playlist_path = os.path.join(self.streams_dir, str(stream_id), "index.m3u8")
        if os.path.exists(playlist_path):
            with open(playlist_path, "r") as f:
                return f.read()
        return None

    def get_segment(self, stream_id: int, segment_name: str) -> Optional[bytes]:
        segment_path = os.path.join(self.streams_dir, str(stream_id), segment_name)
        if os.path.exists(segment_path):
            with open(segment_path, "rb") as f:
                return f.read()
        return None

    def get_stream_dir(self, stream_id: int) -> str:
        return os.path.join(self.streams_dir, str(stream_id))

    def cleanup_stream(self, stream_id: int):
        stream_dir = self.get_stream_dir(stream_id)
        if os.path.exists(stream_dir):
            for f in os.listdir(stream_dir):
                os.remove(os.path.join(stream_dir, f))


hls_handler = HLSHandler()
