"""Registration service for managing pending user registrations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.models import RegisteredUser


class RegistrationService:
    """Manages pending user registrations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self, page: int = 1, per_page: int = 50, status: Optional[int] = None) -> Dict[str, Any]:
        query = self.db.query(RegisteredUser)
        if status is not None:
            query = query.filter(RegisteredUser.status == status)
        total = query.count()
        items = (
            query.order_by(RegisteredUser.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": [self._to_dict(r) for r in items], "total": total, "page": page, "per_page": per_page}

    def get_by_id(self, reg_id: int) -> Optional[Dict[str, Any]]:
        r = self.db.query(RegisteredUser).filter(RegisteredUser.id == reg_id).first()
        if not r:
            return None
        return self._to_dict(r)

    def approve(self, reg_id: int) -> Optional[Dict[str, Any]]:
        r = self.db.query(RegisteredUser).filter(RegisteredUser.id == reg_id).first()
        if not r:
            return None
        r.status = 1
        self.db.commit()
        self.db.refresh(r)
        return self._to_dict(r)

    def reject(self, reg_id: int) -> Optional[Dict[str, Any]]:
        r = self.db.query(RegisteredUser).filter(RegisteredUser.id == reg_id).first()
        if not r:
            return None
        r.status = 2
        self.db.commit()
        self.db.refresh(r)
        return self._to_dict(r)

    def batch_approve(self, reg_ids: List[int]) -> int:
        count = (
            self.db.query(RegisteredUser)
            .filter(RegisteredUser.id.in_(reg_ids))
            .update({RegisteredUser.status: 1}, synchronize_session="fetch")
        )
        self.db.commit()
        return count

    def batch_reject(self, reg_ids: List[int]) -> int:
        count = (
            self.db.query(RegisteredUser)
            .filter(RegisteredUser.id.in_(reg_ids))
            .update({RegisteredUser.status: 2}, synchronize_session="fetch")
        )
        self.db.commit()
        return count

    def delete(self, reg_id: int) -> bool:
        r = self.db.query(RegisteredUser).filter(RegisteredUser.id == reg_id).first()
        if not r:
            return False
        self.db.delete(r)
        self.db.commit()
        return True

    @staticmethod
    def _to_dict(r: RegisteredUser) -> Dict[str, Any]:
        return {
            "id": r.id,
            "username": r.username,
            "email": r.email,
            "ip": r.ip,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
