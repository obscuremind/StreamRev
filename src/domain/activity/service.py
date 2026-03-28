"""User activity service for tracking and querying playback history."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.domain.models import UserActivity, User, Stream


class ActivityService:
    """Manages user playback activity records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(
        self,
        page: int = 1,
        per_page: int = 50,
        user_id: Optional[int] = None,
        stream_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        query = self.db.query(UserActivity).options(
            joinedload(UserActivity.user), joinedload(UserActivity.stream)
        )
        if user_id:
            query = query.filter(UserActivity.user_id == user_id)
        if stream_id:
            query = query.filter(UserActivity.stream_id == stream_id)
        total = query.count()
        items = (
            query.order_by(UserActivity.date_start.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": [self._to_dict(a) for a in items], "total": total, "page": page, "per_page": per_page}

    def get_by_id(self, activity_id: int) -> Optional[Dict[str, Any]]:
        a = self.db.query(UserActivity).filter(UserActivity.id == activity_id).first()
        if not a:
            return None
        return self._to_dict(a)

    def get_by_user(self, user_id: int, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return self.get_all(page=page, per_page=per_page, user_id=user_id)

    def get_ip_history(self, user_id: int) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(
                UserActivity.user_ip,
                UserActivity.geoip_country_code,
                func.count(UserActivity.id).label("count"),
                func.max(UserActivity.date_start).label("last_seen"),
            )
            .filter(UserActivity.user_id == user_id)
            .group_by(UserActivity.user_ip, UserActivity.geoip_country_code)
            .order_by(func.max(UserActivity.date_start).desc())
            .all()
        )
        return [
            {"ip": r.user_ip, "country": r.geoip_country_code, "count": r.count, "last_seen": r.last_seen.isoformat() if r.last_seen else None}
            for r in rows
        ]

    def get_by_stream(self, stream_id: int, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        return self.get_all(page=page, per_page=per_page, stream_id=stream_id)

    def get_stats(self) -> Dict[str, Any]:
        total = self.db.query(func.count(UserActivity.id)).scalar() or 0
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = self.db.query(func.count(UserActivity.id)).filter(UserActivity.date_start >= today).scalar() or 0
        unique_users = self.db.query(func.count(func.distinct(UserActivity.user_id))).scalar() or 0
        unique_streams = self.db.query(func.count(func.distinct(UserActivity.stream_id))).scalar() or 0
        return {
            "total": total,
            "today": today_count,
            "unique_users": unique_users,
            "unique_streams": unique_streams,
        }

    def cleanup(self, days: int = 30) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = self.db.query(UserActivity).filter(UserActivity.date_start < cutoff).delete(synchronize_session="fetch")
        self.db.commit()
        return count

    @staticmethod
    def _to_dict(a: UserActivity) -> Dict[str, Any]:
        return {
            "id": a.id,
            "user_id": a.user_id,
            "username": a.user.username if a.user else None,
            "stream_id": a.stream_id,
            "stream_name": a.stream.stream_display_name if a.stream else None,
            "server_id": a.server_id,
            "user_agent": a.user_agent,
            "user_ip": a.user_ip,
            "container": a.container,
            "country": a.geoip_country_code,
            "date_start": a.date_start.isoformat() if a.date_start else None,
            "date_stop": a.date_stop.isoformat() if a.date_stop else None,
        }
