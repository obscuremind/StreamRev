"""Fingerprint admin API routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.public.controllers.admin.dependencies import get_current_admin
from src.domain.models import User
from src.modules.fingerprint.service import FingerprintService

router = APIRouter(prefix="/api/admin/fingerprint", tags=["Fingerprint"])
_service = FingerprintService()

@router.get("/suspicious")
def list_suspicious(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    mem = _service.get_suspicious_patterns()
    dbr = _service.get_db_suspicious(db)
    seen = {r["user_id"] for r in dbr}
    combined = dbr + [r for r in mem if r["user_id"] not in seen]
    return {"suspicious_users": combined, "total": len(combined)}

@router.get("/user/{user_id}")
def user_history(user_id: int, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return {"user_id": user_id, "history": _service.get_fingerprint_history(user_id), "sharing_analysis": _service.detect_sharing(user_id)}

@router.get("/stats")
def stats(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return _service.get_stats()

@router.post("/detect")
def run_detection(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    mem = _service.get_suspicious_patterns()
    dbr = _service.get_db_suspicious(db)
    seen = {r["user_id"] for r in dbr}
    combined = dbr + [r for r in mem if r["user_id"] not in seen]
    return {"status": "scan_completed", "suspicious_users": len(combined), "high_risk": len([u for u in combined if u.get("risk_level") == "high"]), "results": combined}
