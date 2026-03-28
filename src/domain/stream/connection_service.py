"""Connection management service for admin operations on live connections."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.domain.models import Line, User, Stream, Server


class ConnectionService:
    """Admin-level operations on live connections (Line rows)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(
        self,
        page: int = 1,
        per_page: int = 50,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = self.db.query(Line).options(
            joinedload(Line.user), joinedload(Line.stream), joinedload(Line.server)
        )
        if search:
            like = f"%{search}%"
            query = query.join(Line.user).filter(
                User.username.ilike(like)
            )
        total = query.count()
        items = (
            query.order_by(Line.date.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": [self._to_dict(l) for l in items], "total": total, "page": page, "per_page": per_page}

    def get_stats(self) -> Dict[str, Any]:
        total = self.db.query(func.count(Line.id)).scalar() or 0
        unique_users = self.db.query(func.count(func.distinct(Line.user_id))).scalar() or 0
        unique_ips = self.db.query(func.count(func.distinct(Line.user_ip))).scalar() or 0
        unique_streams = self.db.query(func.count(func.distinct(Line.stream_id))).scalar() or 0
        return {
            "total_connections": total,
            "unique_users": unique_users,
            "unique_ips": unique_ips,
            "unique_streams": unique_streams,
        }

    def kill_connection(self, line_id: int) -> bool:
        line = self.db.query(Line).filter(Line.id == line_id).first()
        if not line:
            return False
        self.db.delete(line)
        self.db.commit()
        return True

    def kill_batch(self, line_ids: List[int]) -> int:
        count = self.db.query(Line).filter(Line.id.in_(line_ids)).delete(synchronize_session="fetch")
        self.db.commit()
        return count

    def kill_by_user(self, user_id: int) -> int:
        count = self.db.query(Line).filter(Line.user_id == user_id).delete(synchronize_session="fetch")
        self.db.commit()
        return count

    def kill_by_ip(self, ip: str) -> int:
        count = self.db.query(Line).filter(Line.user_ip == ip).delete(synchronize_session="fetch")
        self.db.commit()
        return count

    def get_by_stream(self, stream_id: int) -> List[Dict[str, Any]]:
        lines = (
            self.db.query(Line)
            .options(joinedload(Line.user))
            .filter(Line.stream_id == stream_id)
            .order_by(Line.date.desc())
            .all()
        )
        return [self._to_dict(l) for l in lines]

    def get_by_server(self, server_id: int) -> List[Dict[str, Any]]:
        lines = (
            self.db.query(Line)
            .options(joinedload(Line.user), joinedload(Line.stream))
            .filter(Line.server_id == server_id)
            .order_by(Line.date.desc())
            .all()
        )
        return [self._to_dict(l) for l in lines]

    @staticmethod
    def _to_dict(line: Line) -> Dict[str, Any]:
        return {
            "id": line.id,
            "user_id": line.user_id,
            "username": line.user.username if line.user else None,
            "stream_id": line.stream_id,
            "stream_name": line.stream.stream_display_name if line.stream else None,
            "server_id": line.server_id,
            "ip": line.user_ip,
            "user_agent": line.user_agent,
            "container": line.container,
            "country": line.geoip_country_code,
            "bitrate": line.bitrate,
            "date": line.date.isoformat() if line.date else None,
        }
