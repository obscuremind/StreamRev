"""MAG device scanner module."""
MODULE_MANIFEST = {"name": "magscan", "version": "1.0.0", "compatibility": "streamrev-v1"}

from typing import Any
from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger

class Module(ModuleInterface):
    def get_name(self): return "magscan"
    def get_version(self): return "1.0.0"
    def boot(self, app: Any = None):
        from src.modules.magscan.routes import router
        if app is not None:
            app.include_router(router)
        logger.info("MAG Scanner module loaded")
    def get_event_subscribers(self):
        return {"mag.device_connected": self.on_device_connected}
    async def on_device_connected(self, data):
        from src.core.database import SessionLocal
        from src.modules.magscan.service import MagScanService
        if not isinstance(data, dict): return
        mac = data.get("mac", "")
        if not mac: return
        db = SessionLocal()
        try:
            svc = MagScanService(db)
            info = svc.validate_device(mac)
            if info.get("valid") and not info.get("exists"):
                logger.info(f"MAGScan: Unknown device: {mac}")
        except Exception as e:
            logger.error(f"MAGScan: event error: {e}")
        finally:
            db.close()
