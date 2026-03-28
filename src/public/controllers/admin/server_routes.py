from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, Optional

from src.core.database import get_db
from src.domain.models import ServerStream, User
from src.domain.server.service import ServerService
from .dependencies import get_current_admin

router = APIRouter(prefix="/servers", tags=["Admin Servers"])


class ServerCreate(BaseModel):
    server_name: str = ""
    server_ip: str = ""
    server_hardware_id: Optional[str] = None
    domain_name: Optional[str] = None
    http_port: int = 80
    https_port: int = 443
    rtmp_port: int = 1935
    server_protocol: str = "http"
    vpn_ip: Optional[str] = None
    total_clients: int = 0
    is_main: bool = False
    status: int = 0
    parent_id: Optional[int] = None
    network_guaranteed_speed: Optional[int] = None
    total_bandwidth_usage: Optional[int] = None
    ssh_port: int = 22
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    server_key: Optional[str] = None
    timeshift_path: Optional[str] = None
    rtmp_path: Optional[str] = None
    enable_geoip: bool = True


class ServerUpdate(BaseModel):
    server_name: Optional[str] = None
    server_ip: Optional[str] = None
    server_hardware_id: Optional[str] = None
    domain_name: Optional[str] = None
    http_port: Optional[int] = None
    https_port: Optional[int] = None
    rtmp_port: Optional[int] = None
    server_protocol: Optional[str] = None
    vpn_ip: Optional[str] = None
    total_clients: Optional[int] = None
    is_main: Optional[bool] = None
    status: Optional[int] = None
    parent_id: Optional[int] = None
    network_guaranteed_speed: Optional[int] = None
    total_bandwidth_usage: Optional[int] = None
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    server_key: Optional[str] = None
    timeshift_path: Optional[str] = None
    rtmp_path: Optional[str] = None
    enable_geoip: Optional[bool] = None


class StreamAssignRequest(BaseModel):
    stream_id: int


class ServerStreamUpdate(BaseModel):
    pid: Optional[int] = None
    on_demand: Optional[bool] = None
    stream_status: Optional[int] = None
    bitrate: Optional[int] = None
    current_source: Optional[int] = None


@router.get("")
def list_servers(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return [_server_to_dict(s) for s in ServerService(db).get_all()]


@router.get("/stats")
def server_stats(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return ServerService(db).get_stats()


@router.get("/main")
def get_main_server(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    s = ServerService(db).get_main_server()
    if not s:
        raise HTTPException(status_code=404, detail="No main server configured")
    return _server_to_dict(s)


@router.get("/load-balancers")
def list_load_balancers(
    db: Session = Depends(get_db), admin: User = Depends(get_current_admin)
):
    return [_server_to_dict(s) for s in ServerService(db).get_load_balancers()]


@router.post("")
def create_server(
    data: ServerCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return _server_to_dict(ServerService(db).create(data.model_dump(exclude_none=True)))


@router.put("/{server_id}")
def update_server(
    server_id: int,
    data: ServerUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    s = ServerService(db).update(server_id, data.model_dump(exclude_none=True))
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return _server_to_dict(s)


@router.delete("/{server_id}")
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not ServerService(db).delete(server_id):
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "deleted"}


@router.get("/{server_id}/streams")
def list_server_streams(
    server_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = ServerService(db)
    if not svc.get_by_id(server_id):
        raise HTTPException(status_code=404, detail="Server not found")
    return [
        _server_stream_to_dict(ss) for ss in svc.get_server_streams(server_id)
    ]


@router.post("/{server_id}/streams")
def assign_stream_to_server(
    server_id: int,
    body: StreamAssignRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = ServerService(db)
    if not svc.get_by_id(server_id):
        raise HTTPException(status_code=404, detail="Server not found")
    ss = svc.assign_stream(server_id, body.stream_id)
    return _server_stream_to_dict(ss)


@router.put("/{server_id}/streams/{stream_id}")
def update_server_stream(
    server_id: int,
    stream_id: int,
    data: ServerStreamUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = ServerService(db)
    if not svc.get_by_id(server_id):
        raise HTTPException(status_code=404, detail="Server not found")
    ss = (
        db.query(ServerStream)
        .filter(
            ServerStream.server_id == server_id,
            ServerStream.stream_id == stream_id,
        )
        .first()
    )
    if not ss:
        raise HTTPException(status_code=404, detail="Stream not assigned to this server")
    payload = data.model_dump(exclude_none=True)
    for k, v in payload.items():
        setattr(ss, k, v)
    db.commit()
    db.refresh(ss)
    return _server_stream_to_dict(ss)


@router.delete("/{server_id}/streams/{stream_id}")
def unassign_stream_from_server(
    server_id: int,
    stream_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    svc = ServerService(db)
    if not svc.get_by_id(server_id):
        raise HTTPException(status_code=404, detail="Server not found")
    if not svc.unassign_stream(server_id, stream_id):
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {"status": "unassigned"}


@router.get("/{server_id}")
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    s = ServerService(db).get_by_id(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return _server_to_dict(s)


def _server_to_dict(s) -> dict[str, Any]:
    return {
        "id": s.id,
        "server_name": s.server_name,
        "server_ip": s.server_ip,
        "server_hardware_id": s.server_hardware_id,
        "domain_name": s.domain_name,
        "http_port": s.http_port,
        "https_port": s.https_port,
        "rtmp_port": s.rtmp_port,
        "server_protocol": s.server_protocol,
        "vpn_ip": s.vpn_ip,
        "total_clients": s.total_clients,
        "is_main": s.is_main,
        "status": s.status,
        "parent_id": s.parent_id,
        "network_guaranteed_speed": s.network_guaranteed_speed,
        "total_bandwidth_usage": s.total_bandwidth_usage,
        "ssh_port": s.ssh_port,
        "ssh_user": s.ssh_user,
        "enable_geoip": s.enable_geoip,
    }


def _server_stream_to_dict(ss) -> dict[str, Any]:
    return {
        "id": ss.id,
        "server_id": ss.server_id,
        "stream_id": ss.stream_id,
        "pid": ss.pid,
        "on_demand": ss.on_demand,
        "stream_status": ss.stream_status,
        "bitrate": ss.bitrate,
        "current_source": ss.current_source,
    }



@router.get("/detail/{server_id}")
def server_detail(
    server_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    s = ServerService(db).get_by_id(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    streams_count = db.query(ServerStream).filter(ServerStream.server_id == server_id).count()
    active_count = (
        db.query(ServerStream)
        .filter(ServerStream.server_id == server_id, ServerStream.stream_status == 1)
        .count()
    )
    return {
        **_server_to_dict(s),
        "streams_count": streams_count,
        "active_streams": active_count,
    }


@router.get("/monitor/{server_id}")
def monitor_server(
    server_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    s = ServerService(db).get_by_id(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return {
        "server_id": server_id,
        "status": s.status,
        "server_name": s.server_name,
        "server_ip": s.server_ip,
        "total_clients": s.total_clients,
        "bandwidth_usage": s.total_bandwidth_usage,
        "network_speed": s.network_guaranteed_speed,
    }


@router.get("/processes/{server_id}")
def server_processes(
    server_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    s = ServerService(db).get_by_id(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    active_streams = (
        db.query(ServerStream)
        .filter(ServerStream.server_id == server_id, ServerStream.pid.isnot(None))
        .all()
    )
    return {
        "server_id": server_id,
        "processes": [
            {
                "stream_id": ss.stream_id,
                "pid": ss.pid,
                "status": ss.stream_status,
                "bitrate": ss.bitrate,
            }
            for ss in active_streams
        ],
        "total": len(active_streams),
    }


@router.get("/network/{server_id}")
def server_network(
    server_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    s = ServerService(db).get_by_id(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    from sqlalchemy import func
    from src.domain.models import Line
    connection_count = (
        db.query(func.count(Line.id))
        .filter(Line.server_id == server_id)
        .scalar()
        or 0
    )
    return {
        "server_id": server_id,
        "server_ip": s.server_ip,
        "domain_name": s.domain_name,
        "http_port": s.http_port,
        "https_port": s.https_port,
        "rtmp_port": s.rtmp_port,
        "vpn_ip": s.vpn_ip,
        "protocol": s.server_protocol,
        "bandwidth_usage": s.total_bandwidth_usage,
        "guaranteed_speed": s.network_guaranteed_speed,
        "active_connections": connection_count,
    }


@router.post("/restart-service/{server_id}")
def restart_service(
    server_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    s = ServerService(db).get_by_id(server_id)
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    return {
        "status": "restart_queued",
        "server_id": server_id,
        "server_name": s.server_name,
    }
