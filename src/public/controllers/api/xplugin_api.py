"""XPlugin API for Enigma2 device/plugin management (XC_VM–compatible subset)."""

from __future__ import annotations

import os
import random
import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from src.core.auth.password import verify_password
from src.core.config import settings
from src.core.database import get_db
from src.domain.models import User
from src.domain.user.service import UserService

router = APIRouter(tags=["XPlugin API"])

# token -> session: user_id, mac, pending commands, watchdog
_XPLUGIN_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _norm_mac(raw: Optional[str]) -> str:
    return (raw or "").replace(":", "").replace("-", "").strip().upper()


def _random_mac() -> str:
    return ":".join(f"{random.randint(0, 255):02x}" for _ in range(6))


def _find_stalker_by_mac(db: Session, mac_raw: str) -> Optional[User]:
    want = _norm_mac(mac_raw)
    if not want:
        return None
    q = db.query(User).filter(User.is_stalker.is_(True))
    for u in q.all():
        if _norm_mac(u.username) == want:
            return u
    return None


def _validate_session(token: str) -> Dict[str, Any]:
    sess = _XPLUGIN_SESSIONS.get(token)
    if not sess:
        raise HTTPException(status_code=403, detail="Invalid token")
    return sess


@router.get("/xplugin.php")
def xplugin_api(
    db: Session = Depends(get_db),
    username: Optional[str] = Query(None),
    password: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    mac: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
):
    action_l = (action or "").strip().lower()

    if action_l == "gen_mac":
        return {"status": 1, "mac": _random_mac()}

    if action_l == "auth":
        if not mac or not password:
            return {"status": 0, "msg": "mac and password required"}
        user = _find_stalker_by_mac(db, mac)
        if not user or not verify_password(password, user.password):
            return {"status": 0, "msg": "Invalid credentials"}
        if not user.enabled:
            return {"status": 0, "msg": "Account disabled"}
        svc = UserService(db)
        if svc.is_expired(user):
            return {"status": 0, "msg": "Account expired"}
        tkn = secrets.token_hex(24)
        _XPLUGIN_SESSIONS[tkn] = {
            "user_id": user.id,
            "mac": mac,
            "pending": [],
            "watchdog_seconds": 120,
        }
        return {
            "status": 1,
            "token": tkn,
            "username": user.username,
            "password": password,
            "watchdog_seconds": 120,
            "user_info": {
                "username": user.username,
                "auth": 1,
                "status": "Active",
                "exp_date": str(int(user.exp_date.timestamp())) if user.exp_date else None,
                "max_connections": user.max_connections,
            },
        }

    if token and str(token).strip():
        tkn = str(token).strip()
        sess = _XPLUGIN_SESSIONS.get(tkn)
        if sess and not (username and password):
            pending: List[Dict[str, Any]] = list(sess.get("pending") or [])
            sess["pending"] = []
            # Commands use type: message|ssh|screen|reboot_gui|reboot|update|block_ssh|block_telnet|block_ftp|block_all|block_plugin
            return {"status": 1, "commands": pending}
        if not sess and not (username and password):
            return {"status": 0, "msg": "Invalid token"}

    if not action_l and (username or password):
        action_l = "get_info"

    if not username or not password:
        return {"status": 0, "msg": "Invalid credentials"}

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password):
        return {"status": 0, "msg": "Invalid credentials"}
    if not user.enabled:
        return {"status": 0, "msg": "Account disabled"}

    if action_l == "get_info":
        return {
            "status": 1,
            "user_info": {
                "username": user.username,
                "auth": 1,
                "status": "Active" if user.enabled else "Disabled",
                "exp_date": str(int(user.exp_date.timestamp())) if user.exp_date else None,
                "max_connections": user.max_connections,
                "is_trial": user.is_trial,
            },
            "server_info": {
                "url": settings.SERVER_HOST,
                "port": str(settings.SERVER_PORT),
                "protocol": settings.SERVER_PROTOCOL,
            },
        }
    elif action_l == "get_devices":
        return {"status": 1, "devices": []}
    elif action_l == "register_device":
        return {"status": 1, "msg": "Device registered"}
    elif action_l == "remove_device":
        return {"status": 1, "msg": "Device removed"}

    return {"status": 0, "msg": "Unknown action"}


@router.post("/xplugin.php")
async def xplugin_upload(
    request: Request,
    db: Session = Depends(get_db),
    page: Optional[str] = Query(None),
    t: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    file: Optional[UploadFile] = File(None),
):
    if page == "file" and (t or "").strip().lower() == "screen":
        if not token or not str(token).strip():
            raise HTTPException(status_code=403, detail="token required")
        _validate_session(str(token).strip())
        root = settings.CONTENT_DIR or os.path.join(settings.BASE_DIR, "content")
        target_dir = os.path.join(root, "screenshots")
        os.makedirs(target_dir, exist_ok=True)
        safe_tok = "".join(c for c in str(token).strip() if c.isalnum())[:32] or "screen"
        dest = os.path.join(target_dir, f"{safe_tok}.jpg")
        body_file = file
        if body_file is None:
            form = await request.form()
            for key in ("file", "upload", "image", "screen"):
                if key in form:
                    body_file = form[key]
                    break
        if body_file is None:
            raw = await request.body()
            if raw:
                with open(dest, "wb") as f:
                    f.write(raw)
                return {"status": 1, "msg": "screenshot saved", "path": dest}
            raise HTTPException(status_code=400, detail="no file payload")
        content = await body_file.read()
        with open(dest, "wb") as f:
            f.write(content)
        return {"status": 1, "msg": "screenshot saved", "path": dest}
    raise HTTPException(status_code=400, detail="Unsupported upload")
