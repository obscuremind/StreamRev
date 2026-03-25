from sqlalchemy.orm import Session
from typing import Optional, Tuple
from src.domain.models import User, Stream
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

    def authorize_stream(self, user: User, stream_id: int) -> Tuple[bool, Optional[Stream], Optional[str]]:
        stream = self.db.query(Stream).filter(Stream.id == stream_id).first()
        if not stream:
            return False, None, "Stream not found"
        if not stream.enabled:
            return False, None, "Stream offline"
        svc = UserService(self.db)
        if not svc.can_connect(user):
            return False, None, "Max connections reached"
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
