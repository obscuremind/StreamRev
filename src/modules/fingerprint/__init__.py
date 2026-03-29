"""Client fingerprinting module."""
MODULE_MANIFEST = {"name": "fingerprint", "version": "1.0.0", "compatibility": "streamrev-v1"}

import hashlib
from typing import Any
from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger

class FingerprintService:
    @staticmethod
    def generate_fingerprint(user_id, ip, user_agent, stream_id):
        raw = f"{user_id}:{ip}:{user_agent}:{stream_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
    @staticmethod
    def generate_watermark_text(username, ip):
        return f"{username[:8]}_{ip.replace(chr(46), chr(95))[-6:]}"

class Module(ModuleInterface):
    def __init__(self):
        from src.modules.fingerprint.service import FingerprintService as FS
        self._service = FS()
    def get_name(self): return "fingerprint"
    def get_version(self): return "1.0.0"
    def boot(self, app: Any = None):
        from src.modules.fingerprint.routes import router
        if app is not None:
            app.include_router(router)
        logger.info("Fingerprint module loaded")
    def get_event_subscribers(self):
        return {"stream.connected": self.on_stream_connected}
    async def on_stream_connected(self, data):
        if not isinstance(data, dict): return
        uid = data.get("user_id")
        if uid:
            self._service.record_fingerprint(uid, data.get("ip","0.0.0.0"), data.get("user_agent",""), data.get("stream_id",0))
