"""MAG Scanner admin API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.public.controllers.admin.dependencies import get_current_admin
from src.domain.models import User
from src.modules.magscan.service import MagScanService

router = APIRouter(prefix="/api/admin/magscan", tags=["MAG Scanner"])

class ScanRequest(BaseModel):
    subnet: Optional[str] = None

class RegisterRequest(BaseModel):
    mac: str
    user_id: int

@router.get("/devices")
def list_devices(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = MagScanService(db)
    r = svc.scan_network()
    return {"devices": r["devices"], "total": r["total_devices"]}

@router.post("/scan")
def trigger_scan(req: ScanRequest = ScanRequest(), db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = MagScanService(db)
    return svc.scan_network(req.subnet)

@router.post("/register")
def register_device(req: RegisterRequest, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = MagScanService(db)
    r = svc.register_device(req.mac, req.user_id)
    if not r["success"]:
        raise HTTPException(status_code=400, detail=r["error"])
    return r

@router.get("/unregistered")
def list_unregistered(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = MagScanService(db)
    d = svc.get_unregistered()
    return {"devices": d, "total": len(d)}

@router.get("/stats")
def device_stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return MagScanService(db).get_device_stats()
