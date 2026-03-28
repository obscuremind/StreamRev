"""Advanced security service with DB-backed ASN, ISP, IP, and UA blocklists."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.models import BlockedASN, BlockedISP, BlockedIP, BlockedUserAgent


class AdvancedSecurityService:
    """DB-backed security management for ASN, ISP, IP, and user-agent blocking."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- ASN ---
    def get_blocked_asns(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        query = self.db.query(BlockedASN).filter(BlockedASN.blocked.is_(True))
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "items": [self._asn_to_dict(a) for a in items],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    def block_asn(self, asn: int, isp: Optional[str] = None) -> Dict[str, Any]:
        existing = self.db.query(BlockedASN).filter(BlockedASN.asn == asn).first()
        if existing:
            existing.blocked = True
            if isp:
                existing.isp = isp
            self.db.commit()
            self.db.refresh(existing)
            return self._asn_to_dict(existing)
        entry = BlockedASN(asn=asn, isp=isp, blocked=True)
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return self._asn_to_dict(entry)

    def unblock_asn(self, asn_id: int) -> bool:
        entry = self.db.query(BlockedASN).filter(BlockedASN.id == asn_id).first()
        if not entry:
            return False
        entry.blocked = False
        self.db.commit()
        return True

    # --- ISP ---
    def get_blocked_isps(self) -> List[Dict[str, Any]]:
        items = self.db.query(BlockedISP).filter(BlockedISP.enabled.is_(True)).all()
        return [{"id": i.id, "isp_name": i.isp_name, "enabled": i.enabled, "created_at": i.created_at.isoformat() if i.created_at else None} for i in items]

    def block_isp(self, isp_name: str) -> Dict[str, Any]:
        entry = BlockedISP(isp_name=isp_name, enabled=True, created_at=datetime.utcnow())
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return {"id": entry.id, "isp_name": entry.isp_name, "enabled": entry.enabled}

    def unblock_isp(self, isp_id: int) -> bool:
        entry = self.db.query(BlockedISP).filter(BlockedISP.id == isp_id).first()
        if not entry:
            return False
        entry.enabled = False
        self.db.commit()
        return True

    # --- DB-backed IP blocklist ---
    def get_db_blocked_ips(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        query = self.db.query(BlockedIP).filter(BlockedIP.enabled.is_(True))
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "items": [{"id": i.id, "ip": i.ip, "reason": i.reason, "enabled": i.enabled, "created_at": i.created_at.isoformat() if i.created_at else None} for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    def add_blocked_ip(self, ip: str, reason: Optional[str] = None) -> Dict[str, Any]:
        entry = BlockedIP(ip=ip, reason=reason, enabled=True, created_at=datetime.utcnow())
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return {"id": entry.id, "ip": entry.ip, "reason": entry.reason}

    def remove_blocked_ip(self, ip_id: int) -> bool:
        entry = self.db.query(BlockedIP).filter(BlockedIP.id == ip_id).first()
        if not entry:
            return False
        self.db.delete(entry)
        self.db.commit()
        return True

    # --- DB-backed UA blocklist ---
    def get_db_blocked_uas(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        query = self.db.query(BlockedUserAgent).filter(BlockedUserAgent.enabled.is_(True))
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "items": [{"id": i.id, "pattern": i.pattern, "enabled": i.enabled, "created_at": i.created_at.isoformat() if i.created_at else None} for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    def add_blocked_ua(self, pattern: str) -> Dict[str, Any]:
        entry = BlockedUserAgent(pattern=pattern, enabled=True, created_at=datetime.utcnow())
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return {"id": entry.id, "pattern": entry.pattern}

    def remove_blocked_ua(self, ua_id: int) -> bool:
        entry = self.db.query(BlockedUserAgent).filter(BlockedUserAgent.id == ua_id).first()
        if not entry:
            return False
        self.db.delete(entry)
        self.db.commit()
        return True

    # --- Country blocking (settings-based) ---
    def get_blocked_countries(self) -> List[str]:
        from src.domain.server.settings_service import SettingsService
        raw = SettingsService(self.db).get("blocked_countries", "[]")
        try:
            return json.loads(raw) if isinstance(raw, str) else list(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_blocked_countries(self, countries: List[str]) -> List[str]:
        from src.domain.server.settings_service import SettingsService
        SettingsService(self.db).set("blocked_countries", countries, "json")
        return countries

    @staticmethod
    def _asn_to_dict(a: BlockedASN) -> Dict[str, Any]:
        return {
            "id": a.id,
            "asn": a.asn,
            "isp": a.isp,
            "domain": a.domain,
            "country": a.country,
            "num_ips": a.num_ips,
            "type": a.asn_type,
            "blocked": a.blocked,
        }
