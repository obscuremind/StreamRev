from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.core.database import get_db
from src.core.auth import create_access_token, create_refresh_token
from src.domain.user.service import UserService

router = APIRouter(prefix="/auth", tags=["Admin Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


@router.post("/login", response_model=TokenResponse)
def admin_login(request: LoginRequest, db: Session = Depends(get_db)):
    svc = UserService(db)
    user = svc.authenticate(request.username, request.password)
    if not user or not user.is_admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials or not an admin")
    access_token = create_access_token({"sub": str(user.id), "role": "admin"})
    refresh_token = create_refresh_token({"sub": str(user.id), "role": "admin"})
    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token,
        user_id=user.id, username=user.username,
    )
