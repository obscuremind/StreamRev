"""Watch folder admin API routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.public.controllers.admin.dependencies import get_current_admin
from src.domain.models import User
from src.modules.watch.service import WatchFolderService

router = APIRouter(prefix="/api/admin/watch", tags=["Watch Folder"])

class AddDirRequest(BaseModel):
    path: str

class RemoveDirRequest(BaseModel):
    path: str

class ScanRequest(BaseModel):
    path: Optional[str] = None

class ImportRequest(BaseModel):
    files: List[str] = []
    path: Optional[str] = None
    category_id: Optional[int] = None
    stream_type: str = "movie"

@router.get("/directories")
def list_watch_dirs(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = WatchFolderService(db)
    return {"directories": svc.get_watch_dirs()}

@router.post("/directories")
def add_watch_dir(req: AddDirRequest, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = WatchFolderService(db)
    return {"directories": svc.add_watch_dir(req.path)}

@router.delete("/directories")
def remove_watch_dir(req: RemoveDirRequest, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = WatchFolderService(db)
    return {"directories": svc.remove_watch_dir(req.path)}

@router.post("/scan")
def trigger_scan(req: ScanRequest = ScanRequest(), db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = WatchFolderService(db)
    results = svc.scan_directory(req.path) if req.path else svc.scan_all()
    return {"status": "completed", "files_found": len(results), "results": results}

@router.get("/scan-results")
def last_scan_results(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = WatchFolderService(db)
    results = svc.get_last_scan_results()
    return {"results": results, "total": len(results)}

@router.post("/import")
def import_files(req: ImportRequest, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    svc = WatchFolderService(db)
    if req.files:
        result = svc.import_files(req.files, category_id=req.category_id, stream_type=req.stream_type)
    elif req.path:
        result = svc.auto_import(req.path, category_id=req.category_id, stream_type=req.stream_type)
    else:
        raise HTTPException(status_code=400, detail="Provide files or path")
    return {"status": "completed", **result}
