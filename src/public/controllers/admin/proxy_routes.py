"""Proxy management admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from src.core.database import get_db
from src.domain.models import User
from src.domain.proxy.service import ProxyService
from .dependencies import get_current_admin

router = APIRouter(prefix="/proxies", tags=["Admin Proxies"])


class ProxyCreate(BaseModel):
    proxy_name: str = ""
    proxy_url: str = ""
    proxy_type: str = "http"
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    enabled: bool = True
    server_id: Optional[int] = None


class ProxyUpdate(BaseModel):
    proxy_name: Optional[str] = None
    proxy_url: Optional[str] = None
    proxy_type: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    enabled: Optional[bool] = None
    server_id: Optional[int] = None


@router.get("")
def list_proxies(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"proxies": ProxyService(db).get_all()}


@router.post("/create")
def create_proxy(
    data: ProxyCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ProxyService(db).create(data.model_dump(exclude_none=True))


@router.put("/{proxy_id}")
def update_proxy(
    proxy_id: int,
    data: ProxyUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = ProxyService(db).update(proxy_id, data.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return result


@router.delete("/{proxy_id}")
def delete_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not ProxyService(db).delete(proxy_id):
        raise HTTPException(status_code=404, detail="Proxy not found")
    return {"status": "deleted"}


@router.post("/test/{proxy_id}")
def test_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return ProxyService(db).test_proxy(proxy_id)


@router.post("/toggle/{proxy_id}")
def toggle_proxy(
    proxy_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = ProxyService(db).toggle(proxy_id)
    if not result:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return result
