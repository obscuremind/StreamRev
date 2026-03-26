"""Watch folder module - monitors directories for new media files and auto-imports them."""
import os
from typing import Any, Dict, List
from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger


class WatchService:
    def __init__(self, watch_dirs: List[str] = None):
        self.watch_dirs = watch_dirs or []

    def scan(self) -> List[Dict[str, Any]]:
        found = []
        for d in self.watch_dirs:
            if not os.path.isdir(d):
                continue
            for root, dirs, files in os.walk(d):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in ('.mp4', '.mkv', '.avi', '.ts', '.m3u8', '.flv', '.mov'):
                        fp = os.path.join(root, f)
                        found.append({
                            "filename": f,
                            "path": fp,
                            "size": os.path.getsize(fp),
                            "extension": ext,
                        })
        return found


class Module(ModuleInterface):
    def get_name(self) -> str:
        return "watch"

    def get_version(self) -> str:
        return "1.0.0"

    def boot(self, app: Any = None) -> None:
        logger.info("Watch folder module loaded")

    def register_routes(self, router: Any = None) -> None:
        pass

    def get_event_subscribers(self) -> dict:
        return {"vod.scan_requested": self.on_scan_requested}

    async def on_scan_requested(self, data):
        logger.info(f"Watch: Scan requested")
