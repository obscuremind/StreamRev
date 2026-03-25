"""Ministra/Stalker Portal middleware integration module."""
from typing import Any
from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger


class Module(ModuleInterface):
    def get_name(self) -> str:
        return "ministra"

    def get_version(self) -> str:
        return "1.0.0"

    def boot(self, app: Any = None) -> None:
        logger.info("Ministra/Stalker portal module loaded")

    def register_routes(self, router: Any = None) -> None:
        pass

    def get_event_subscribers(self) -> dict:
        return {}
