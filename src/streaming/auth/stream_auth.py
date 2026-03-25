import json
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from src.domain.models import Bouquet, User, Stream
from src.domain.user.service import UserService
from src.core.auth.password import verify_password


class StreamAuth:
    def __init__(self, db: Session):
        self.db = db

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[User], Optional[str]]:
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            return False, None, "User not found"
        if not verify_password(password, user.password):
            return False, None, "Invalid password"
        if not user.enabled:
            return False, None, "Account disabled"
        svc = UserService(self.db)
        if svc.is_expired(user):
            return False, None, "Account expired"
        return True, user, None

    def check_bouquet_access(self, user: User, stream_id: int) -> bool:
        """Return True if user may access stream_id based on bouquet channel lists."""
        if user.is_admin:
            return True
        raw = (user.bouquet or "").strip()
        if not raw:
            return True
        bouquet_ids: list[int] = []
        for part in raw.split(","):
            p = part.strip()
            if p.isdigit():
                bouquet_ids.append(int(p))
        if not bouquet_ids:
            return True
        for bid in bouquet_ids:
            b = self.db.query(Bouquet).filter(Bouquet.id == bid).first()
            if not b:
                continue
            try:
                channels = json.loads(b.bouquet_channels or "[]")
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(channels, list):
                continue
            for c in channels:
                try:
                    if int(c) == stream_id:
                        return True
                except (TypeError, ValueError):
                    if c == stream_id:
                        return True
        return False

    def check_geoip_allowed(self, user: User, client_ip: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Placeholder for GeoIP enforcement (e.g. MaxMind / panel country rules). Always allows."""
        _ = (user, client_ip)
        return True, None

    def authorize_stream(
        self,
        user: User,
        stream_id: int,
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Tuple[bool, Optional[Stream], Optional[str]]:
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return False, None, "Stream not found"
        if not stream.enabled:
            return False, None, "Stream offline"
        svc = UserService(self.db)
        if not svc.can_connect(user):
            return False, None, "Max connections reached"
        if not self.check_bouquet_access(user, stream_id):
            return False, None, "Stream not in allowed bouquets"
        if user.allowed_user_agents:
            ua = user_agent or ""
            if not self.check_user_agent_allowed(user, ua):
                return False, None, "User-Agent not allowed"
        ok_geo, geo_err = self.check_geoip_allowed(user, client_ip)
        if not ok_geo:
            return False, None, geo_err or "GeoIP not allowed"
        return True, stream, None

    def check_ip_allowed(self, user: User, ip: str) -> bool:
        if not user.allowed_ips:
            return True
        allowed = [x.strip() for x in user.allowed_ips.split(",") if x.strip()]
        if not allowed:
            return True
        return ip in allowed

    def check_user_agent_allowed(self, user: User, ua: str) -> bool:
        if not user.allowed_user_agents:
            return True
        allowed = [x.strip() for x in user.allowed_user_agents.split(",") if x.strip()]
        if not allowed:
            return True
        return any(a in ua for a in allowed)
