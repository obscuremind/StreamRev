"""End-user domain service: CRUD, auth, connection limits, batch ops, stats."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.core.auth.password import hash_password, verify_password
from src.core.util.encryption import generate_token
from src.domain.models import Line, User, UserActivity


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(
        self,
        page: int = 1,
        per_page: int = 50,
        search: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        query = self.db.query(User)
        if search:
            query = query.filter(User.username.ilike(f"%{search.strip()}%"))
        if enabled is not None:
            query = query.filter(User.enabled == enabled)
        total = query.count()
        items = (
            query.order_by(User.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password):
            return None
        if not user.enabled:
            return None
        return user

    def create(self, data: Dict[str, Any]) -> User:
        payload = dict(data)
        if "password" in payload:
            payload["password"] = hash_password(payload["password"])
        user = User(**payload)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user_id: int, data: Dict[str, Any]) -> Optional[User]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        payload = dict(data)
        if payload.get("password"):
            payload["password"] = hash_password(payload["password"])
        else:
            payload.pop("password", None)
        for key, value in payload.items():
            if hasattr(user, key):
                setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if not user:
            return False
        self.db.query(Line).filter(Line.user_id == user_id).delete()
        self.db.query(UserActivity).filter(UserActivity.user_id == user_id).delete()
        self.db.delete(user)
        self.db.commit()
        return True

    def toggle_status(self, user_id: int) -> Optional[User]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.enabled = not user.enabled
        self.db.commit()
        self.db.refresh(user)
        return user

    @staticmethod
    def is_expired(user: User) -> bool:
        if user.exp_date is None:
            return False
        now = datetime.utcnow()
        exp = user.exp_date
        if exp.tzinfo is not None:
            exp = exp.replace(tzinfo=None)
        return now > exp

    def get_active_connections(self, user_id: int) -> int:
        return (
            self.db.query(func.count(Line.id)).filter(Line.user_id == user_id).scalar()
            or 0
        )

    def can_connect(self, user: User) -> bool:
        if not user.enabled:
            return False
        if self.is_expired(user):
            return False
        if self.get_active_connections(user.id) >= user.max_connections:
            return False
        return True

    def get_stats(self) -> Dict[str, int]:
        now = datetime.utcnow()
        active_q = self.db.query(func.count(User.id)).filter(
            User.enabled.is_(True),
            or_(User.exp_date.is_(None), User.exp_date > now),
        )
        expired_q = self.db.query(func.count(User.id)).filter(
            User.exp_date.isnot(None),
            User.exp_date <= now,
        )
        return {
            "total": self.db.query(func.count(User.id)).scalar() or 0,
            "active": active_q.scalar() or 0,
            "expired": expired_q.scalar() or 0,
            "disabled": self.db.query(func.count(User.id))
            .filter(User.enabled.is_(False))
            .scalar()
            or 0,
            "trial": self.db.query(func.count(User.id))
            .filter(User.is_trial.is_(True))
            .scalar()
            or 0,
            "online": self.db.query(func.count(func.distinct(Line.user_id))).scalar()
            or 0,
        }

    def generate_credentials(self) -> Dict[str, str]:
        return {"username": generate_token(8), "password": generate_token(8)}

    def batch_delete(self, user_ids: List[int]) -> int:
        if not user_ids:
            return 0
        self.db.query(Line).filter(Line.user_id.in_(user_ids)).delete(
            synchronize_session="fetch"
        )
        self.db.query(UserActivity).filter(UserActivity.user_id.in_(user_ids)).delete(
            synchronize_session="fetch"
        )
        count = (
            self.db.query(User)
            .filter(User.id.in_(user_ids))
            .delete(synchronize_session="fetch")
        )
        self.db.commit()
        return count

    def batch_toggle(self, user_ids: List[int], enabled: bool) -> int:
        if not user_ids:
            return 0
        count = (
            self.db.query(User)
            .filter(User.id.in_(user_ids))
            .update({User.enabled: enabled}, synchronize_session="fetch")
        )
        self.db.commit()
        return count

    def get_online_users(self) -> List[Dict[str, Any]]:
        lines = self.db.query(Line).order_by(Line.date.desc()).all()
        return [
            {
                "line_id": line.id,
                "user_id": line.user_id,
                "stream_id": line.stream_id,
                "server_id": line.server_id,
                "user_ip": line.user_ip,
                "user_agent": line.user_agent,
                "container": line.container,
                "date": line.date.isoformat() if line.date else None,
            }
            for line in lines
        ]
