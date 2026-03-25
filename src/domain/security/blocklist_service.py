"""IP/User-Agent blocklist service for security."""

import json
from typing import List, Set

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
    def __init__(self, db: Session):
        self.db = db
        self._settings = SettingsService(db)
        self._attempts = {}

    def record_attempt(self, ip: str, success: bool):
        if success:
            self._attempts.pop(ip, None)
            return
        if ip not in self._attempts:
            self._attempts[ip] = 0
        self._attempts[ip] += 1

    def is_blocked(self, ip: str) -> bool:
        max_attempts = int(self._settings.get("max_login_attempts", "10"))
        return self._attempts.get(ip, 0) >= max_attempts

    def reset(self, ip: str):
        self._attempts.pop(ip, None)

    def get_blocked_ips(self) -> List[str]:
        max_attempts = int(self._settings.get("max_login_attempts", "10"))
        return [ip for ip, count in self._attempts.items() if count >= max_attempts]
