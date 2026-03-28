from fastapi import APIRouter, Depends, HTTPException
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



# --- Advanced security: DB-backed blocklists ---
from src.domain.security.advanced_security_service import AdvancedSecurityService


class ASNBlockRequest(BaseModel):
    asn: int
    isp: str = ""


class ISPBlockRequest(BaseModel):
    isp_name: str


class DBIPBlockRequest(BaseModel):
    ip: str
    reason: str = ""


class DBUABlockRequest(BaseModel):
    pattern: str


class CountryBlockRequest(BaseModel):
    countries: list[str]


@router.get("/blocked-asns")
def list_blocked_asns(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return AdvancedSecurityService(db).get_blocked_asns(page=page, per_page=per_page)


@router.post("/block-asn")
def block_asn(
    data: ASNBlockRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return AdvancedSecurityService(db).block_asn(data.asn, isp=data.isp)


@router.post("/unblock-asn/{asn_id}")
def unblock_asn(
    asn_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not AdvancedSecurityService(db).unblock_asn(asn_id):
        raise HTTPException(status_code=404, detail="ASN entry not found")
    return {"status": "unblocked"}


@router.get("/blocked-isps")
def list_blocked_isps(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"isps": AdvancedSecurityService(db).get_blocked_isps()}


@router.post("/block-isp")
def block_isp_entry(
    data: ISPBlockRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return AdvancedSecurityService(db).block_isp(data.isp_name)


@router.post("/unblock-isp/{isp_id}")
def unblock_isp(
    isp_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not AdvancedSecurityService(db).unblock_isp(isp_id):
        raise HTTPException(status_code=404, detail="ISP entry not found")
    return {"status": "unblocked"}


@router.get("/db-blocked-ips")
def list_db_blocked_ips(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return AdvancedSecurityService(db).get_db_blocked_ips(page=page, per_page=per_page)


@router.post("/db-block-ip")
def add_db_blocked_ip(
    data: DBIPBlockRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return AdvancedSecurityService(db).add_blocked_ip(data.ip, reason=data.reason)


@router.delete("/db-blocked-ip/{ip_id}")
def remove_db_blocked_ip(
    ip_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not AdvancedSecurityService(db).remove_blocked_ip(ip_id):
        raise HTTPException(status_code=404, detail="Blocked IP not found")
    return {"status": "removed"}


@router.get("/db-blocked-uas")
def list_db_blocked_uas(
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return AdvancedSecurityService(db).get_db_blocked_uas(page=page, per_page=per_page)


@router.post("/db-block-ua")
def add_db_blocked_ua(
    data: DBUABlockRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return AdvancedSecurityService(db).add_blocked_ua(data.pattern)


@router.delete("/db-blocked-ua/{ua_id}")
def remove_db_blocked_ua(
    ua_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if not AdvancedSecurityService(db).remove_blocked_ua(ua_id):
        raise HTTPException(status_code=404, detail="Blocked UA not found")
    return {"status": "removed"}


@router.get("/blocked-countries")
def list_blocked_countries(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"countries": AdvancedSecurityService(db).get_blocked_countries()}


@router.post("/block-countries")
def set_blocked_countries(
    data: CountryBlockRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return {"countries": AdvancedSecurityService(db).set_blocked_countries(data.countries)}
