"""Off-air handler - serves placeholder content when a stream is offline."""
import os
from typing import Optional
from src.core.config import settings


class OffAirHandler:
    def __init__(self):
        self.off_air_image = os.path.join(settings.CONTENT_DIR, "off_air.jpg")
        self.off_air_ts = os.path.join(settings.CONTENT_DIR, "off_air.ts")

    def get_off_air_image(self) -> Optional[bytes]:
        if os.path.exists(self.off_air_image):
            with open(self.off_air_image, "rb") as f:
                return f.read()
        return None

    def get_off_air_stream(self) -> Optional[bytes]:
        if os.path.exists(self.off_air_ts):
            with open(self.off_air_ts, "rb") as f:
                return f.read()
        return None

    def is_configured(self) -> bool:
        return os.path.exists(self.off_air_image) or os.path.exists(self.off_air_ts)

    def generate_off_air_m3u8(self, stream_id: int) -> str:
        return (
            "#EXTM3U\n"
            "#EXT-X-VERSION:3\n"
            "#EXT-X-TARGETDURATION:10\n"
            "#EXT-X-MEDIA-SEQUENCE:0\n"
            "#EXTINF:10.0,\n"
            "/static/off_air.ts\n"
            "#EXT-X-ENDLIST\n"
        )


off_air_handler = OffAirHandler()
