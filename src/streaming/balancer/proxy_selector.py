from typing import Optional
from sqlalchemy.orm import Session
from src.domain.models import Server, ServerStream


class ProxySelector:
    def __init__(self, db: Session):
        self.db = db

    def select_server(self, stream_id: int, exclude_server_id: Optional[int] = None) -> Optional[Server]:
        query = self.db.query(Server).join(ServerStream).filter(
            ServerStream.stream_id == stream_id,
            Server.status == 1,
        )
        if exclude_server_id:
            query = query.filter(Server.id != exclude_server_id)
        servers = query.all()
        if not servers:
            return None
        return min(servers, key=lambda s: s.total_clients or 0)

    def get_stream_url(self, server: Server, stream_id: int, container: str = "ts") -> str:
        protocol = server.server_protocol or "http"
        port = server.https_port if protocol == "https" else server.http_port
        return f"{protocol}://{server.server_ip}:{port}/live/{stream_id}.{container}"

    def get_player_live_url(
        self,
        server: Server,
        username: str,
        password: str,
        stream_id: int,
        container: str = "ts",
    ) -> str:
        """Xtream-style live URL including credentials (panel-compatible path)."""
        protocol = server.server_protocol or "http"
        port = server.https_port if protocol == "https" else server.http_port
        host = (server.domain_name or "").strip() or server.server_ip
        return (
            f"{protocol}://{host}:{port}/live/{username}/{password}/"
            f"{stream_id}.{container}"
        )
