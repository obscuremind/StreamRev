"""Stream authentication middleware - shared headers/token handling for streaming endpoints."""
from typing import Dict, Optional, Tuple


class StreamAuthMiddleware:
    @staticmethod
    def extract_credentials_from_path(path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        parts = path.strip("/").split("/")
        if len(parts) >= 3:
            username = parts[-3] if len(parts) >= 3 else None
            password = parts[-2] if len(parts) >= 2 else None
            stream_ext = parts[-1] if parts else None
            return username, password, stream_ext
        return None, None, None

    @staticmethod
    def extract_stream_id_and_container(stream_ext: str) -> Tuple[Optional[int], str]:
        if not stream_ext:
            return None, "ts"
        parts = stream_ext.rsplit(".", 1)
        try:
            stream_id = int(parts[0])
        except (ValueError, IndexError):
            return None, "ts"
        container = parts[1] if len(parts) > 1 else "ts"
        return stream_id, container

    @staticmethod
    def get_client_info(request) -> Dict[str, str]:
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        forwarded_for = request.headers.get("x-forwarded-for", "")
        real_ip = request.headers.get("x-real-ip", "")
        return {
            "ip": real_ip or (forwarded_for.split(",")[0].strip() if forwarded_for else client_ip),
            "user_agent": user_agent,
            "forwarded_for": forwarded_for,
        }

    @staticmethod
    def build_stream_headers(container: str = "ts") -> Dict[str, str]:
        mime_types = {
            "ts": "video/mp2t",
            "m3u8": "application/vnd.apple.mpegurl",
            "mp4": "video/mp4",
            "mkv": "video/x-matroska",
            "avi": "video/x-msvideo",
            "flv": "video/x-flv",
        }
        return {
            "Content-Type": mime_types.get(container, "application/octet-stream"),
            "Cache-Control": "no-cache, no-store",
            "Access-Control-Allow-Origin": "*",
            "Connection": "keep-alive",
        }
