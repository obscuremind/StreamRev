import os
import subprocess
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from src.core.config import settings
from src.domain.models import User

from .dependencies import get_current_admin

router = APIRouter(prefix="/backups", tags=["Admin Backups"])


@router.get("")
def list_backups(admin: User = Depends(get_current_admin)):
    backup_dir = os.path.join(settings.BASE_DIR, "backups")
    if not os.path.isdir(backup_dir):
        return {"backups": []}
    backups = []
    for f in sorted(os.listdir(backup_dir), reverse=True):
        fp = os.path.join(backup_dir, f)
        if os.path.isfile(fp):
            backups.append(
                {
                    "filename": f,
                    "size": os.path.getsize(fp),
                    "created": datetime.fromtimestamp(os.path.getctime(fp)).isoformat(),
                }
            )
    return {"backups": backups}


@router.post("/create")
def create_backup(admin: User = Depends(get_current_admin)):
    backup_dir = os.path.join(settings.BASE_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.sql"
    filepath = os.path.join(backup_dir, filename)
    try:
        cmd = [
            "mysqldump",
            "-h",
            settings.DB_HOST,
            "-P",
            str(settings.DB_PORT),
            "-u",
            settings.DB_USER,
            f"-p{settings.DB_PASSWORD}",
            settings.DB_NAME,
        ]
        with open(filepath, "w", encoding="utf-8") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=300)
        if result.returncode != 0:
            os.remove(filepath)
            return {"status": "error", "detail": result.stderr.decode()[:500]}
        return {"status": "created", "filename": filename, "size": os.path.getsize(filepath)}
    except FileNotFoundError:
        return {"status": "error", "detail": "mysqldump not found. Manual backup required."}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.delete("/{filename}")
def delete_backup(filename: str, admin: User = Depends(get_current_admin)):
    backup_dir = os.path.join(settings.BASE_DIR, "backups")
    safe_name = os.path.basename(filename)
    filepath = os.path.join(backup_dir, safe_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Backup not found")
    os.remove(filepath)
    return {"status": "deleted", "filename": safe_name}
