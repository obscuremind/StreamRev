"""IP/User-Agent blocklist service for security."""

import json
from typing import ClassVar, Dict, List, Set

from sqlalchemy.orm import Session

from src.domain.server.settings_service import SettingsService


class BlocklistService:
    def __init__(self, db: Session):
        self.db = db
        self._settings = SettingsService(db)

    def get_blocked_ips(self) -> Set[str]:
        raw = self._settings.get("blocked_ips", "[]")
        try:
            if isinstance(raw, str):
                return set(json.loads(raw))
            if isinstance(raw, list):
                return set(raw)
            return set()
        except (json.JSONDecodeError, TypeError):
            return set()

    def block_ip(self, ip: str) -> bool:
        blocked = self.get_blocked_ips()
        blocked.add(ip)
        self._settings.set("blocked_ips", list(blocked), "json")
        return True

    def unblock_ip(self, ip: str) -> bool:
        blocked = self.get_blocked_ips()
        blocked.discard(ip)
        self._settings.set("blocked_ips", list(blocked), "json")
        return True

    def is_ip_blocked(self, ip: str) -> bool:
        return ip in self.get_blocked_ips()

    def get_blocked_user_agents(self) -> Set[str]:
        raw = self._settings.get("blocked_user_agents", "[]")
        try:
            if isinstance(raw, str):
                return set(json.loads(raw))
            if isinstance(raw, list):
                return set(raw)
            return set()
        except (json.JSONDecodeError, TypeError):
            return set()

    def block_user_agent(self, ua_pattern: str) -> bool:
        blocked = self.get_blocked_user_agents()
        blocked.add(ua_pattern)
        self._settings.set("blocked_user_agents", list(blocked), "json")
        return True

    def is_user_agent_blocked(self, ua: str) -> bool:
        for pattern in self.get_blocked_user_agents():
            if pattern.lower() in ua.lower():
                return True
        return False


class BruteforceGuard:
    """Tracks failed auth attempts per IP across requests (process-wide)."""

    _attempts: ClassVar[Dict[str, int]] = {}

    def __init__(self, db: Session):
        self.db = db
        self._settings = SettingsService(db)

    def record_attempt(self, ip: str, success: bool):
        if success:
            BruteforceGuard._attempts.pop(ip, None)
            return
        BruteforceGuard._attempts[ip] = BruteforceGuard._attempts.get(ip, 0) + 1

    def is_blocked(self, ip: str) -> bool:
        max_attempts = int(self._settings.get("max_login_attempts", "10"))
        return BruteforceGuard._attempts.get(ip, 0) >= max_attempts

    def reset(self, ip: str):
        BruteforceGuard._attempts.pop(ip, None)

    def get_blocked_ips(self) -> List[str]:
        max_attempts = int(self._settings.get("max_login_attempts", "10"))
        return [ip for ip, count in BruteforceGuard._attempts.items() if count >= max_attempts]
