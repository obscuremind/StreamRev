"""MAG device scanner service."""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.core.logging.logger import logger
from src.domain.models import MagDevice, User

MAC_PATTERN = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")

class MagScanService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def is_valid_mac(mac):
        return bool(MAC_PATTERN.match(mac))

    @staticmethod
    def normalize_mac(mac):
        mac = mac.upper().strip()
        if len(mac) == 12 and ":" not in mac:
            mac = ":".join(mac[i:i+2] for i in range(0, 12, 2))
        return mac

    def scan_network(self, subnet=None):
        all_dev = self.db.query(MagDevice).all()
        reg = [d for d in all_dev if d.user_id and d.user_id > 0]
        unreg = [d for d in all_dev if not d.user_id or d.user_id == 0]
        return {"subnet": subnet or "all", "total_devices": len(all_dev), "registered": len(reg), "unregistered": len(unreg),
                "devices": [{"id": d.mag_id or d.id, "mac": d.mac, "user_id": d.user_id, "enabled": d.enabled, "registered": bool(d.user_id and d.user_id > 0)} for d in all_dev],
                "scanned_at": datetime.utcnow().isoformat()}

    def validate_device(self, mac):
        mac = self.normalize_mac(mac)
        if not self.is_valid_mac(mac):
            return {"valid": False, "error": "Invalid MAC format", "mac": mac}
        device = self.db.query(MagDevice).filter(MagDevice.mac == mac).first()
        if device:
            return {"valid": True, "mac": mac, "exists": True, "device_id": device.mag_id or device.id, "user_id": device.user_id, "enabled": device.enabled}
        return {"valid": True, "mac": mac, "exists": False}

    def register_device(self, mac, user_id):
        mac = self.normalize_mac(mac)
        if not self.is_valid_mac(mac):
            return {"success": False, "error": "Invalid MAC format"}
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}
        device = self.db.query(MagDevice).filter(MagDevice.mac == mac).first()
        if device:
            device.user_id = user_id
            device.enabled = True
        else:
            device = MagDevice(mac=mac, user_id=user_id, enabled=True, lock_device=False)
            self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return {"success": True, "device_id": device.mag_id or device.id, "mac": mac, "user_id": user_id}

    def get_unregistered(self):
        devices = self.db.query(MagDevice).filter((MagDevice.user_id == None) | (MagDevice.user_id == 0)).all()
        return [{"id": d.mag_id or d.id, "mac": d.mac, "enabled": d.enabled} for d in devices]

    def get_device_stats(self):
        total = self.db.query(MagDevice).count()
        enabled = self.db.query(MagDevice).filter(MagDevice.enabled == True).count()
        registered = self.db.query(MagDevice).filter(MagDevice.user_id != None, MagDevice.user_id != 0).count()
        return {"total_devices": total, "enabled": enabled, "disabled": total - enabled, "registered": registered, "unregistered": total - registered}
