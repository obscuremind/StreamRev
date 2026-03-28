"""Theft detection admin API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.public.controllers.admin.dependencies import get_current_admin
from src.domain.models import User
from src.modules.theft_detection.service import TheftDetectionService

router = APIRouter(prefix="/api/admin/theft", tags=["Theft Detection"])
_service = TheftDetectionService()

@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    a = _service.get_alerts()
    return {"alerts": a, "total": len(a)}

@router.get("/suspicious")
def list_suspicious(threshold: int = Query(3, ge=1), db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    mem = _service.get_suspicious_users(threshold)
    dbr = _service.detect_credential_sharing_db(db, threshold)
    seen = {r["user_id"] for r in dbr}
    combined = dbr + [r for r in mem if r["user_id"] not in seen]
    return {"suspicious_users": combined, "total": len(combined)}

@router.get("/report")
def get_report(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return _service.get_report(db)

@router.post("/scan")
def run_scan(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    sharing = _service.detect_credential_sharing()
    redist = _service.detect_redistribution()
    db_sharing = _service.detect_credential_sharing_db(db)
    return {"status": "scan_completed", "credential_sharing": len(sharing), "redistribution": len(redist), "db_sharing": len(db_sharing), "results": {"sharing": sharing[:20], "redistribution": redist[:20], "db_sharing": db_sharing[:20]}}

@router.post("/block/{user_id}")
def block_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    r = _service.auto_block(user_id, db)
    if not r["success"]:
        raise HTTPException(status_code=404, detail=r["error"])
    return r

@router.post("/clear")
def clear_data(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    r = _service.clear_data()
    return {"status": "cleared", **r}

@router.get("/stats")
def theft_stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return _service.get_stats()
