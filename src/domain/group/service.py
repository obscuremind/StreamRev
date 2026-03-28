"""User group management service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.models import UserGroup, User


class UserGroupService:
    """Manages user groups."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> List[Dict[str, Any]]:
        items = self.db.query(UserGroup).order_by(UserGroup.group_id.asc()).all()
        return [self._to_dict(g) for g in items]

    def get_by_id(self, group_id: int) -> Optional[Dict[str, Any]]:
        g = self.db.query(UserGroup).filter(UserGroup.group_id == group_id).first()
        if not g:
            return None
        return self._to_dict(g)

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        group = UserGroup(**data)
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return self._to_dict(group)

    def update(self, group_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        g = self.db.query(UserGroup).filter(UserGroup.group_id == group_id).first()
        if not g:
            return None
        for key, value in data.items():
            if hasattr(g, key):
                setattr(g, key, value)
        self.db.commit()
        self.db.refresh(g)
        return self._to_dict(g)

    def delete(self, group_id: int) -> bool:
        g = self.db.query(UserGroup).filter(UserGroup.group_id == group_id).first()
        if not g:
            return False
        if not g.can_delete:
            return False
        self.db.query(User).filter(User.member_group_id == group_id).update(
            {User.member_group_id: None}, synchronize_session="fetch"
        )
        self.db.delete(g)
        self.db.commit()
        return True

    def get_users(self, group_id: int) -> List[Dict[str, Any]]:
        users = self.db.query(User).filter(User.member_group_id == group_id).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "enabled": u.enabled,
                "max_connections": u.max_connections,
                "exp_date": u.exp_date.isoformat() if u.exp_date else None,
            }
            for u in users
        ]

    def add_users(self, group_id: int, user_ids: List[int]) -> int:
        g = self.db.query(UserGroup).filter(UserGroup.group_id == group_id).first()
        if not g:
            return 0
        count = (
            self.db.query(User)
            .filter(User.id.in_(user_ids))
            .update({User.member_group_id: group_id}, synchronize_session="fetch")
        )
        self.db.commit()
        return count

    def remove_users(self, group_id: int, user_ids: List[int]) -> int:
        count = (
            self.db.query(User)
            .filter(User.id.in_(user_ids), User.member_group_id == group_id)
            .update({User.member_group_id: None}, synchronize_session="fetch")
        )
        self.db.commit()
        return count

    @staticmethod
    def _to_dict(g: UserGroup) -> Dict[str, Any]:
        return {
            "group_id": g.group_id,
            "group_name": g.group_name,
            "can_delete": g.can_delete,
            "packages": g.packages,
        }
