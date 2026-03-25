from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone
from src.core.database import get_db
from src.core.auth import create_access_token, decode_access_token
from src.domain.line.service import ResellerService, PackageService
from src.domain.user.service import UserService
from src.domain.models import Reseller

router = APIRouter(tags=["Reseller API"])
security = HTTPBearer()


def get_current_reseller(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Reseller:
    payload = decode_access_token(credentials.credentials)
    if not payload or payload.get("role") != "reseller":
        raise HTTPException(status_code=401, detail="Invalid token")
    reseller = db.query(Reseller).filter(Reseller.id == int(payload["sub"])).first()
    if not reseller or reseller.status != 1:
        raise HTTPException(status_code=403, detail="Reseller access denied")
    return reseller


class ResellerLoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    max_connections: int = 1
    package_id: Optional[int] = None
    bouquet: Optional[str] = None
    exp_date: Optional[datetime] = None
    notes: Optional[str] = None


class ExtendUserRequest(BaseModel):
    user_id: int
    days: int = 30


@router.post("/login")
def reseller_login(req: ResellerLoginRequest, db: Session = Depends(get_db)):
    svc = ResellerService(db)
    reseller = svc.authenticate(req.username, req.password)
    if not reseller:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(reseller.id), "role": "reseller"})
    return {
        "access_token": token, "token_type": "bearer",
        "reseller_id": reseller.id, "username": reseller.username,
        "credits": reseller.credits,
    }


@router.get("/info")
def reseller_info(reseller: Reseller = Depends(get_current_reseller)):
    return {
        "id": reseller.id, "username": reseller.username,
        "credits": reseller.credits, "status": reseller.status,
    }


@router.get("/users")
def reseller_users(
    page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), reseller: Reseller = Depends(get_current_reseller),
):
    svc = UserService(db)
    result = svc.get_all(page=page, per_page=per_page)
    result["items"] = [
        {
            "id": u.id, "username": u.username, "max_connections": u.max_connections,
            "exp_date": str(u.exp_date) if u.exp_date else None,
            "enabled": u.enabled, "is_trial": u.is_trial,
            "created_at": str(u.created_at) if u.created_at else None,
        }
        for u in result["items"]
    ]
    return result


@router.post("/users/create")
def reseller_create_user(
    data: CreateUserRequest, db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    reseller_svc = ResellerService(db)
    user_svc = UserService(db)

    existing = user_svc.get_by_username(data.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    cost = 1
    if data.package_id:
        pkg_svc = PackageService(db)
        pkg = pkg_svc.get_by_id(data.package_id)
        if pkg:
            cost = pkg.official_credits or 1

    if reseller.credits < cost:
        raise HTTPException(status_code=400, detail="Insufficient credits")

    user_data = data.model_dump(exclude_none=True)
    user_data.pop("package_id", None)
    if "notes" in user_data:
        user_data["reseller_notes"] = user_data.pop("notes")
    user = user_svc.create(user_data)
    reseller_svc.use_credits(reseller.id, cost)

    return {"user_id": user.id, "username": user.username, "credits_remaining": reseller.credits - cost}


@router.post("/users/extend")
def reseller_extend_user(
    data: ExtendUserRequest, db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    user_svc = UserService(db)
    reseller_svc = ResellerService(db)

    user = user_svc.get_by_id(data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if reseller.credits < 1:
        raise HTTPException(status_code=400, detail="Insufficient credits")

    new_exp = datetime.now(timezone.utc) + timedelta(days=data.days)
    if user.exp_date and user.exp_date > datetime.now(timezone.utc):
        new_exp = user.exp_date + timedelta(days=data.days)

    user_svc.update(data.user_id, {"exp_date": new_exp})
    reseller_svc.use_credits(reseller.id, 1)

    return {"user_id": user.id, "new_exp_date": str(new_exp)}


@router.delete("/users/{user_id}")
def reseller_delete_user(
    user_id: int, db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    if not UserService(db).delete(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "deleted"}


@router.post("/users/{user_id}/toggle")
def reseller_toggle_user(
    user_id: int, db: Session = Depends(get_db),
    reseller: Reseller = Depends(get_current_reseller),
):
    user = UserService(db).toggle_status(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.id, "enabled": user.enabled}


@router.get("/packages")
def reseller_packages(db: Session = Depends(get_db), reseller: Reseller = Depends(get_current_reseller)):
    pkgs = PackageService(db).get_all()
    return [
        {
            "id": p.id, "package_name": p.package_name,
            "is_trial": p.is_trial, "trial_credits": p.trial_credits,
            "official_credits": p.official_credits,
            "max_connections": p.max_connections,
        }
        for p in pkgs
    ]
