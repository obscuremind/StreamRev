from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.domain.models import User
from src.domain.security.blocklist_service import BlocklistService, BruteforceGuard

from .dependencies import get_current_admin

router = APIRouter(prefix="/security", tags=["Admin Security"])


class IPAction(BaseModel):
    ip: str


class UAAction(BaseModel):
    pattern: str


@router.get("/blocked-ips")
def list_blocked_ips(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return {"ips": list(BlocklistService(db).get_blocked_ips())}


@router.post("/block-ip")
def block_ip(data: IPAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    BlocklistService(db).block_ip(data.ip)
    return {"status": "blocked", "ip": data.ip}


@router.post("/unblock-ip")
def unblock_ip(data: IPAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    BlocklistService(db).unblock_ip(data.ip)
    return {"status": "unblocked", "ip": data.ip}


@router.get("/blocked-user-agents")
def list_blocked_uas(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    return {"patterns": list(BlocklistService(db).get_blocked_user_agents())}


@router.post("/block-user-agent")
def block_ua(data: UAAction, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    BlocklistService(db).block_user_agent(data.pattern)
    return {"status": "blocked", "pattern": data.pattern}


@router.get("/bruteforce-blocked")
def bruteforce_blocked(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    guard = BruteforceGuard(db)
    return {"blocked_ips": guard.get_blocked_ips()}
