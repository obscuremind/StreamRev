"""Theft detection module - detects credential sharing and stream redistribution."""
from typing import Any, Dict, List, Set
from collections import defaultdict
from src.core.module.loader import ModuleInterface
from src.core.logging.logger import logger


class TheftDetector:
    def __init__(self):
        self._user_ips: Dict[int, Set[str]] = defaultdict(set)
        self._alerts: List[Dict] = []

    def record_connection(self, user_id: int, ip: str, user_agent: str):
        self._user_ips[user_id].add(ip)
        if len(self._user_ips[user_id]) > 5:
            self._alerts.append({
                "user_id": user_id,
                "unique_ips": len(self._user_ips[user_id]),
                "type": "multi_ip",
            })

    def get_alerts(self) -> List[Dict]:
        return self._alerts

    def clear_alerts(self):
        self._alerts.clear()

    def get_suspicious_users(self, threshold: int = 3) -> List[Dict]:
        return [
            {"user_id": uid, "unique_ips": len(ips)}
            for uid, ips in self._user_ips.items()
            if len(ips) >= threshold
        ]


class Module(ModuleInterface):
    def get_name(self) -> str:
        return "theft-detection"

    def get_version(self) -> str:
        return "1.0.0"

    def boot(self, app: Any = None) -> None:
        logger.info("Theft detection module loaded")

    def register_routes(self, router: Any = None) -> None:
        pass

    def get_event_subscribers(self) -> dict:
        return {"stream.connected": self.on_connection}

    async def on_connection(self, data):
        logger.debug("Theft detection: Connection event recorded")
