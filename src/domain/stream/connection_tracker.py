"""Track active stream connections (Line rows + in-process index)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.domain.models import Line, Stream, User

_line_meta: Dict[int, Dict[str, Any]] = {}
_by_stream: Dict[int, Set[int]] = {}
_by_user: Dict[int, Set[int]] = {}


def _register_line(line: Line) -> None:
    _line_meta[line.id] = {
        "user_id": line.user_id,
        "stream_id": line.stream_id,
        "server_id": line.server_id,
        "ip": line.user_ip,
        "user_agent": line.user_agent,
        "container": line.container,
        "date": line.date,
    }
    _by_stream.setdefault(line.stream_id, set()).add(line.id)
    _by_user.setdefault(line.user_id, set()).add(line.id)


def _unregister_line(line_id: int, user_id: int, stream_id: int) -> None:
    _line_meta.pop(line_id, None)
    if stream_id in _by_stream:
        _by_stream[stream_id].discard(line_id)
        if not _by_stream[stream_id]:
            del _by_stream[stream_id]
    if user_id in _by_user:
        _by_user[user_id].discard(line_id)
        if not _by_user[user_id]:
            del _by_user[user_id]


class ConnectionTracker:
    def __init__(self, db: Session) -> None:
        self.db = db

    def track_connection(
        self,
        user_id: int,
        stream_id: int,
        server_id: int,
        ip: Optional[str],
        user_agent: Optional[str],
        container: str,
    ) -> Line:
        line = Line(
            user_id=user_id,
            stream_id=stream_id,
            server_id=server_id,
            user_ip=ip,
            user_agent=user_agent,
            container=container,
            date=datetime.utcnow(),
        )
        self.db.add(line)
        self.db.commit()
        self.db.refresh(line)
        _register_line(line)
        return line

    def remove_connection(self, user_id: int, stream_id: int) -> int:
        lines = (
            self.db.query(Line)
            .filter(Line.user_id == user_id, Line.stream_id == stream_id)
            .all()
        )
        n = 0
        for line in lines:
            _unregister_line(line.id, line.user_id, line.stream_id)
            self.db.delete(line)
            n += 1
        self.db.commit()
        return n

    def get_connections_by_stream(self, stream_id: int) -> List[Line]:
        return (
            self.db.query(Line)
            .options(joinedload(Line.user), joinedload(Line.stream))
            .filter(Line.stream_id == stream_id)
            .order_by(Line.date.desc())
            .all()
        )

    def get_connections_by_user(self, user_id: int) -> List[Line]:
        return (
            self.db.query(Line)
            .options(joinedload(Line.user), joinedload(Line.stream))
            .filter(Line.user_id == user_id)
            .order_by(Line.date.desc())
            .all()
        )

    def get_live_connections(self) -> List[Dict[str, Any]]:
        lines = (
            self.db.query(Line)
            .options(joinedload(Line.user), joinedload(Line.stream))
            .order_by(Line.date.desc())
            .all()
        )
        out: List[Dict[str, Any]] = []
        for line in lines:
            u = line.user
            s = line.stream
            out.append(
                {
                    "line_id": line.id,
                    "user_id": line.user_id,
                    "username": u.username if u else None,
                    "stream_id": line.stream_id,
                    "stream_name": s.stream_display_name if s else None,
                    "server_id": line.server_id,
                    "ip": line.user_ip,
                    "user_agent": line.user_agent,
                    "container": line.container,
                    "date": line.date.isoformat() if line.date else None,
                }
            )
        return out

    def get_connection_count(self) -> int:
        return self.db.query(func.count(Line.id)).scalar() or 0

    def cleanup_stale(self, max_age_seconds: int) -> int:
        cutoff = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        lines = self.db.query(Line).filter(Line.date < cutoff).all()
        n = 0
        for line in lines:
            _unregister_line(line.id, line.user_id, line.stream_id)
            self.db.delete(line)
            n += 1
        self.db.commit()
        return n
