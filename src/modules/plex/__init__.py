"""Plex integration module."""
MODULE_MANIFEST = {"name": "plex", "version": "1.0.0", "compatibility": "streamrev-v1"}

from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger
from typing import Any

class Module(ModuleInterface):
    def get_name(self) -> str:
        return "plex"
    def get_version(self) -> str:
        return "1.0.0"
    def boot(self, app: Any = None) -> None:
        from src.modules.plex.routes import router
        if app is not None:
            app.include_router(router)
        logger.info("Plex module loaded")
    def get_event_subscribers(self) -> dict:
        return {}
