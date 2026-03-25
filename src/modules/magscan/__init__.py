"""MAG device scanning module - discovers and manages MAG devices on network."""
from typing import Any
from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger


class MagScanner:
    @staticmethod
    def parse_mac(mac: str) -> str:
        return mac.upper().replace("-", ":").strip()

    @staticmethod
    def validate_mac(mac: str) -> bool:
        import re
        return bool(re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', mac.upper().replace("-", ":")))


class Module(ModuleInterface):
    def get_name(self) -> str:
        return "magscan"

    def get_version(self) -> str:
        return "1.0.0"

    def boot(self, app: Any = None) -> None:
        logger.info("MAG scanner module loaded")

    def register_routes(self, router: Any = None) -> None:
        pass

    def get_event_subscribers(self) -> dict:
        return {}
