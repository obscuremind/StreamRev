"""XPlugin API for device/plugin management."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.config import settings
from src.domain.models import User
from src.core.auth.password import verify_password

router = APIRouter(tags=["XPlugin API"])


@router.get("/xplugin.php")
def xplugin_api(
    username: str = Query(...), password: str = Query(...),
    action: str = Query("get_info"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password):
        return {"status": 0, "msg": "Invalid credentials"}
    if not user.enabled:
        return {"status": 0, "msg": "Account disabled"}

    if action == "get_info":
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
    elif action == "get_devices":
        return {"status": 1, "devices": []}
    elif action == "register_device":
        return {"status": 1, "msg": "Device registered"}
    elif action == "remove_device":
        return {"status": 1, "msg": "Device removed"}

    return {"status": 0, "msg": "Unknown action"}
