"""Client fingerprinting module for stream protection and abuse detection."""
import hashlib
from typing import Any, Dict
from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger


class FingerprintService:
    @staticmethod
    def generate_fingerprint(user_id: int, ip: str, user_agent: str, stream_id: int) -> str:
        raw = f"{user_id}:{ip}:{user_agent}:{stream_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    @staticmethod
    def generate_watermark_text(username: str, ip: str) -> str:
        return f"{username[:8]}_{ip.replace('.', '')[-6:]}"


class Module(ModuleInterface):
    def get_name(self) -> str:
        return "fingerprint"

    def get_version(self) -> str:
        return "1.0.0"

    def boot(self, app: Any = None) -> None:
        logger.info("Fingerprint module loaded")

    def register_routes(self, router: Any = None) -> None:
        pass

    def get_event_subscribers(self) -> dict:
        return {"stream.connected": self.on_stream_connected}

    async def on_stream_connected(self, data):
        logger.debug(f"Fingerprint: Stream connection event")
