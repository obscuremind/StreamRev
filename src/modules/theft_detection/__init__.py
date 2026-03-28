"""Theft detection module."""
from typing import Any
from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger

class TheftDetector:
    @staticmethod
    def check_sharing(user_connections):
        unique_ips = set()
        for c in user_connections:
            if isinstance(c, dict):
                unique_ips.add(c.get("ip", ""))
        return {"suspicious": len(unique_ips) > 3, "unique_ips": len(unique_ips)}

class Module(ModuleInterface):
    def __init__(self):
        from src.modules.theft_detection.service import TheftDetectionService
        self._service = TheftDetectionService()
    def get_name(self): return "theft_detection"
    def get_version(self): return "1.0.0"
    def boot(self, app: Any = None):
        from src.modules.theft_detection.routes import router
        if app is not None:
            app.include_router(router)
        logger.info("Theft Detection module loaded")
    def get_event_subscribers(self):
        return {"stream.connected": self.on_stream_connected, "user.blocked": self.on_user_blocked}
    async def on_stream_connected(self, data):
        if not isinstance(data, dict): return
        uid = data.get("user_id")
        if not uid: return
        self._service.record_connection(uid, data.get("ip","0.0.0.0"), data.get("user_agent",""))
        sharing = self._service.detect_credential_sharing()
        for s in sharing:
            if s["user_id"] == uid and s["risk_level"] == "high":
                logger.warning(f"TheftDetection: High risk user {uid} ({s['unique_ips']} IPs)")
                self._service._add_alert("credential_sharing", uid, f"User {uid}: {s['unique_ips']} unique IPs")
    async def on_user_blocked(self, data):
        if isinstance(data, dict) and data.get("user_id"):
            logger.info(f"TheftDetection: User {data['user_id']} blocked")
