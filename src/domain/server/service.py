"""Server nodes: CRUD, stream assignment, load balancers, stats."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.models import Server, ServerStream


class ServerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> List[Server]:
        return self.db.query(Server).order_by(Server.id.asc()).all()

    def get_by_id(self, server_id: int) -> Optional[Server]:
        return self.db.query(Server).filter(Server.id == server_id).first()

    def get_main_server(self) -> Optional[Server]:
        return self.db.query(Server).filter(Server.is_main.is_(True)).first()

    def create(self, data: Dict[str, Any]) -> Server:
        server = Server(**data)
        self.db.add(server)
        self.db.commit()
        self.db.refresh(server)
        return server

    def update(self, server_id: int, data: Dict[str, Any]) -> Optional[Server]:
        server = self.get_by_id(server_id)
        if not server:
            return None
        for key, value in data.items():
            if hasattr(server, key):
                setattr(server, key, value)
        self.db.commit()
        self.db.refresh(server)
        return server

    def delete(self, server_id: int) -> bool:
        server = self.get_by_id(server_id)
        if not server:
            return False
        self.db.query(ServerStream).filter(ServerStream.server_id == server_id).delete()
        self.db.delete(server)
        self.db.commit()
        return True

    def assign_stream(self, server_id: int, stream_id: int) -> ServerStream:
        existing = (
            self.db.query(ServerStream)
            .filter(
                ServerStream.server_id == server_id,
                ServerStream.stream_id == stream_id,
            )
            .first()
        )
        if existing:
            return existing
        ss = ServerStream(server_id=server_id, stream_id=stream_id)
        self.db.add(ss)
        self.db.commit()
        self.db.refresh(ss)
        return ss

    def unassign_stream(self, server_id: int, stream_id: int) -> bool:
        count = (
            self.db.query(ServerStream)
            .filter(
                ServerStream.server_id == server_id,
                ServerStream.stream_id == stream_id,
            )
            .delete()
        )
        self.db.commit()
        return count > 0

    def get_server_streams(self, server_id: int) -> List[ServerStream]:
        return (
            self.db.query(ServerStream)
            .filter(ServerStream.server_id == server_id)
            .all()
        )

    def get_load_balancers(self) -> List[Server]:
        """Child servers attached to a parent (typical LB / edge nodes)."""
        q = self.db.query(Server).filter(Server.parent_id.isnot(None))
        rows = q.order_by(Server.id.asc()).all()
        if rows:
            return rows
        return (
            self.db.query(Server)
            .filter(Server.is_main.is_(False))
            .order_by(Server.id.asc())
            .all()
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": self.db.query(func.count(Server.id)).scalar() or 0,
            "online": self.db.query(func.count(Server.id))
            .filter(Server.status == 1)
            .scalar()
            or 0,
            "offline": self.db.query(func.count(Server.id))
            .filter(Server.status == 0)
            .scalar()
            or 0,
            "main_servers": self.db.query(func.count(Server.id))
            .filter(Server.is_main.is_(True))
            .scalar()
            or 0,
        }
