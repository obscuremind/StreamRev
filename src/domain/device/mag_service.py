"""MAG device user management (User rows with is_mag=True)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.core.auth.password import hash_password
from src.domain.models import Line, User, UserActivity


class MagService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _mag_query(self):
        return self.db.query(User).filter(User.is_mag.is_(True))

    def get_all_mags(
        self,
        page: int = 1,
        per_page: int = 50,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = self._mag_query()
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

    def get_mag_by_id(self, user_id: int) -> Optional[User]:
        return self._mag_query().filter(User.id == user_id).first()

    def create_mag(self, data: Dict[str, Any]) -> User:
        payload = dict(data)
        payload["is_mag"] = True
        if "password" in payload:
            payload["password"] = hash_password(payload["password"])
        user = User(**payload)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_mag(self, user_id: int, data: Dict[str, Any]) -> Optional[User]:
        user = self.get_mag_by_id(user_id)
        if not user:
            return None
        payload = dict(data)
        if payload.get("password"):
            payload["password"] = hash_password(payload["password"])
        else:
            payload.pop("password", None)
        payload["is_mag"] = True
        for key, value in payload.items():
            if hasattr(user, key):
                setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_mag(self, user_id: int) -> bool:
        user = self.get_mag_by_id(user_id)
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
        payload["is_mag"] = True
        users = (
            self._mag_query()
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
        mag_ids = [
            row[0]
            for row in self.db.query(User.id)
            .filter(User.id.in_(user_ids), User.is_mag.is_(True))
            .all()
        ]
        if not mag_ids:
            return 0
        self.db.query(Line).filter(Line.user_id.in_(mag_ids)).delete(
            synchronize_session="fetch"
        )
        self.db.query(UserActivity).filter(UserActivity.user_id.in_(mag_ids)).delete(
            synchronize_session="fetch"
        )
        count = (
            self.db.query(User)
            .filter(User.id.in_(mag_ids))
            .delete(synchronize_session="fetch")
        )
        self.db.commit()
        return count
