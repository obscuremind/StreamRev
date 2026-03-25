"""Enigma2 device user management (User rows with is_stalker=True)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.core.auth.password import hash_password
from src.domain.models import Line, User, UserActivity


class EnigmaService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _enigma_query(self):
        return self.db.query(User).filter(User.is_stalker.is_(True))

    def get_all_enigmas(
        self,
        page: int = 1,
        per_page: int = 50,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = self._enigma_query()
        if search:
            query = query.filter(User.username.ilike(f"%{search.strip()}%"))
        total = query.count()
        items = (
            query.order_by(User.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def get_enigma_by_id(self, user_id: int) -> Optional[User]:
        return self._enigma_query().filter(User.id == user_id).first()

    def create_enigma(self, data: Dict[str, Any]) -> User:
        payload = dict(data)
        payload["is_stalker"] = True
        if "password" in payload:
            payload["password"] = hash_password(payload["password"])
        user = User(**payload)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_enigma(self, user_id: int, data: Dict[str, Any]) -> Optional[User]:
        user = self.get_enigma_by_id(user_id)
        if not user:
            return None
        payload = dict(data)
        if payload.get("password"):
            payload["password"] = hash_password(payload["password"])
        else:
            payload.pop("password", None)
        payload["is_stalker"] = True
        for key, value in payload.items():
            if hasattr(user, key):
                setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_enigma(self, user_id: int) -> bool:
        user = self.get_enigma_by_id(user_id)
        if not user:
            return False
        self.db.query(Line).filter(Line.user_id == user_id).delete()
        self.db.query(UserActivity).filter(UserActivity.user_id == user_id).delete()
        self.db.delete(user)
        self.db.commit()
        return True

    def mass_update(self, user_ids: List[int], data: Dict[str, Any]) -> int:
        if not user_ids:
            return 0
        payload = dict(data)
        if payload.get("password"):
            payload["password"] = hash_password(payload["password"])
        else:
            payload.pop("password", None)
        payload["is_stalker"] = True
        users = (
            self._enigma_query()
            .filter(User.id.in_(user_ids))
            .all()
        )
        for user in users:
            for key, value in payload.items():
                if hasattr(user, key):
                    setattr(user, key, value)
        self.db.commit()
        return len(users)

    def mass_delete(self, user_ids: List[int]) -> int:
        if not user_ids:
            return 0
        stalker_ids = [
            row[0]
            for row in self.db.query(User.id)
            .filter(User.id.in_(user_ids), User.is_stalker.is_(True))
            .all()
        ]
        if not stalker_ids:
            return 0
        self.db.query(Line).filter(Line.user_id.in_(stalker_ids)).delete(
            synchronize_session="fetch"
        )
        self.db.query(UserActivity).filter(UserActivity.user_id.in_(stalker_ids)).delete(
            synchronize_session="fetch"
        )
        count = (
            self.db.query(User)
            .filter(User.id.in_(stalker_ids))
            .delete(synchronize_session="fetch")
        )
        self.db.commit()
        return count
