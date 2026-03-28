"""Live connections admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.stream.connection_service import ConnectionService
from .dependencies import get_current_admin

router = APIRouter(prefix="/connections", tags=["Admin Connections"])


class KillBatchRequest(BaseModel):
    line_ids: List[int]


class KillByIPRequest(BaseModel):
    ip: str


@router.get("")
def list_connections(
    page: int = 1,
    per_page: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ConnectionService(db).get_all(page=page, per_page=per_page, search=search)


@router.get("/stats")
def connection_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ConnectionService(db).get_stats()


@router.post("/kill/{line_id}")
def kill_connection(
    line_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not ConnectionService(db).kill_connection(line_id):
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"status": "killed", "line_id": line_id}


@router.post("/kill-batch")
def kill_batch(
    data: KillBatchRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = ConnectionService(db).kill_batch(data.line_ids)
    return {"status": "killed", "count": count}


@router.post("/kill-by-user/{user_id}")
def kill_by_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = ConnectionService(db).kill_by_user(user_id)
    return {"status": "killed", "count": count}


@router.post("/kill-by-ip")
def kill_by_ip(
    data: KillByIPRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    count = ConnectionService(db).kill_by_ip(data.ip)
    return {"status": "killed", "count": count}


@router.get("/by-stream/{stream_id}")
def connections_by_stream(
    stream_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"connections": ConnectionService(db).get_by_stream(stream_id)}


@router.get("/by-server/{server_id}")
def connections_by_server(
    server_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"connections": ConnectionService(db).get_by_server(server_id)}
