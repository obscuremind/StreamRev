"""Ministra/Stalker portal service."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.core.config import settings
from src.core.logging.logger import logger
from src.domain.models import User, MagDevice, Setting

DEFAULT_CONFIG = {
    "portal_url": "", "portal_name": "StreamRev Portal", "portal_theme": "starter",
    "portal_logo": "", "timezone": "UTC", "ntp_server": "pool.ntp.org",
    "allow_stb_registration": True, "max_stb_per_user": 2, "default_locale": "en", "enabled": True,
}

class MinistraService:
    def __init__(self, db: Session):
        self.db = db

    def get_portal_config(self):
        row = self.db.query(Setting).filter(Setting.key == "ministra_config").first()
        if row and row.value:
            try:
                return {**DEFAULT_CONFIG, **json.loads(row.value)}
            except json.JSONDecodeError:
                pass
        return dict(DEFAULT_CONFIG)

    def set_portal_config(self, config):
        current = self.get_portal_config()
        current.update(config)
        row = self.db.query(Setting).filter(Setting.key == "ministra_config").first()
        val = json.dumps(current)
        if row:
            row.value = val
        else:
            row = Setting(key="ministra_config", value=val, value_type="json")
            self.db.add(row)
        self.db.commit()
        return current

    def sync_users(self):
        stalker = self.db.query(User).filter((User.is_stalker == True) | (User.is_mag == True)).all()
        created = updated = 0
        for u in stalker:
            device = self.db.query(MagDevice).filter(MagDevice.user_id == u.id).first()
            if device:
                if device.enabled != u.enabled:
                    device.enabled = u.enabled; updated += 1
            else:
                self.db.add(MagDevice(mac=getattr(u, "mac", None) or "00:1A:79:00:00:00", user_id=u.id, enabled=u.enabled, lock_device=False))
                created += 1
        self.db.commit()
        return {"total_stalker_users": len(stalker), "devices_created": created, "devices_updated": updated, "synced_at": datetime.utcnow().isoformat()}

    def get_stb_profiles(self):
        devices = self.db.query(MagDevice).all()
        profiles = []
        for d in devices:
            user = self.db.query(User).filter(User.id == d.user_id).first() if d.user_id else None
            profiles.append({"device_id": d.mag_id or d.id, "mac": d.mac, "user_id": d.user_id, "username": user.username if user else None, "enabled": d.enabled, "locked": d.lock_device})
        return profiles

    def generate_portal_url(self, user_id):
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user: return None
        cfg = self.get_portal_config()
        portal = cfg.get("portal_url", "") or f"{settings.SERVER_PROTOCOL}://{settings.SERVER_HOST}:{settings.SERVER_PORT}/stalker_portal"
        return f"{portal}/c/index.html?mac={user.mac or ''}&sn=&type=STB"

    def get_status(self):
        cfg = self.get_portal_config()
        return {"module": "ministra", "enabled": cfg.get("enabled", True), "portal_url": cfg.get("portal_url", ""), "total_stb_devices": self.db.query(MagDevice).count(), "stalker_users": self.db.query(User).filter((User.is_stalker == True) | (User.is_mag == True)).count()}
