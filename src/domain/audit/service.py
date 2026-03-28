"""Audit log service for tracking admin actions."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.models import AuditLog


class AuditService:
    """Manages audit log entries for admin actions."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self, page: int = 1, per_page: int = 50, action: Optional[str] = None) -> Dict[str, Any]:
        query = self.db.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        total = query.count()
        items = (
            query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": [self._to_dict(a) for a in items], "total": total, "page": page, "per_page": per_page}

    def get_by_id(self, audit_id: int) -> Optional[Dict[str, Any]]:
        a = self.db.query(AuditLog).filter(AuditLog.id == audit_id).first()
        if not a:
            return None
        return self._to_dict(a)

    def get_by_admin(self, admin_id: int, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        query = self.db.query(AuditLog).filter(AuditLog.admin_id == admin_id)
        total = query.count()
        items = (
            query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": [self._to_dict(a) for a in items], "total": total, "page": page, "per_page": per_page}

    def get_by_entity(self, entity_type: str, entity_id: int, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        query = self.db.query(AuditLog).filter(
            AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id
        )
        total = query.count()
        items = (
            query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": [self._to_dict(a) for a in items], "total": total, "page": page, "per_page": per_page}

    def log_action(
        self,
        admin_id: int,
        admin_username: str,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        entry = AuditLog(
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            created_at=datetime.utcnow(),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return self._to_dict(entry)

    def cleanup(self, days: int = 90) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = self.db.query(AuditLog).filter(AuditLog.created_at < cutoff).delete(synchronize_session="fetch")
        self.db.commit()
        return count

    @staticmethod
    def _to_dict(a: AuditLog) -> Dict[str, Any]:
        return {
            "id": a.id,
            "admin_id": a.admin_id,
            "admin_username": a.admin_username,
            "action": a.action,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "details": a.details,
            "ip_address": a.ip_address,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
