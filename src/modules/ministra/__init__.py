"""Ministra/Stalker portal module."""
from typing import Any
from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger

class Module(ModuleInterface):
    def get_name(self): return "ministra"
    def get_version(self): return "1.0.0"
    def boot(self, app: Any = None):
        from src.modules.ministra.routes import router
        if app is not None:
            app.include_router(router)
        logger.info("Ministra module loaded")
    def get_event_subscribers(self):
        return {"user.created": self.on_user_created}
    async def on_user_created(self, data):
        from src.core.database import SessionLocal
        from src.modules.ministra.service import MinistraService
        if not isinstance(data, dict): return
        uid = data.get("user_id")
        is_stb = data.get("is_stalker", False) or data.get("is_mag", False)
        if not uid or not is_stb: return
        db = SessionLocal()
        try:
            MinistraService(db).sync_users()
        except Exception as e:
            logger.error(f"Ministra sync error: {e}")
        finally:
            db.close()
