"""Fingerprint service."""
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from sqlalchemy.orm import Session
from src.core.config import settings
from src.core.logging.logger import logger
from src.domain.models import UserActivity

class FingerprintService:
    _fingerprint_history: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    _user_ips: Dict[int, Set[str]] = defaultdict(set)
    _user_agents: Dict[int, Set[str]] = defaultdict(set)

    @staticmethod
    def generate_fingerprint(user_id, ip, user_agent, stream_id):
        raw = f"{user_id}:{ip}:{user_agent}:{stream_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    @staticmethod
    def generate_watermark_text(username, ip):
        return f"{username[:8]}_{ip.replace('.', '')[-6:]}"

    def record_fingerprint(self, user_id, ip, user_agent, stream_id):
        fp = self.generate_fingerprint(user_id, ip, user_agent, stream_id)
        self._fingerprint_history[user_id].append({"fingerprint": fp, "ip": ip, "user_agent": user_agent, "stream_id": stream_id, "timestamp": datetime.utcnow().isoformat()})
        self._user_ips[user_id].add(ip)
        self._user_agents[user_id].add(user_agent)
        return fp

    def detect_sharing(self, user_id):
        ips = self._user_ips.get(user_id, set())
        uas = self._user_agents.get(user_id, set())
        h = self._fingerprint_history.get(user_id, [])
        return {"user_id": user_id, "unique_ips": len(ips), "unique_user_agents": len(uas), "total_connections": len(h), "is_suspicious": len(ips) > 3 or len(uas) > 5, "ips": list(ips), "user_agents": list(uas)[:10]}

    def get_fingerprint_history(self, user_id):
        return self._fingerprint_history.get(user_id, [])

    def get_suspicious_patterns(self):
        suspicious = []
        for uid, ips in self._user_ips.items():
            if len(ips) > 3:
                suspicious.append({"user_id": uid, "unique_ips": len(ips), "unique_user_agents": len(self._user_agents.get(uid, set())), "total_connections": len(self._fingerprint_history.get(uid, [])), "risk_level": "high" if len(ips) > 10 else "medium"})
        suspicious.sort(key=lambda x: x["unique_ips"], reverse=True)
        return suspicious

    @staticmethod
    def add_watermark_to_stream(stream_url, text):
        escaped = text.replace("'", "'\\''")
        return f"{settings.FFMPEG_PATH} -i \"{stream_url}\" -vf \"drawtext=text='{escaped}':fontsize=12:fontcolor=white@0.3:x=(w-text_w)/2:y=h-30\" -c:a copy -f mpegts pipe:1"

    def verify_fingerprint(self, fingerprint, user_id):
        return any(e["fingerprint"] == fingerprint for e in self._fingerprint_history.get(user_id, []))

    def get_stats(self):
        suspicious = self.get_suspicious_patterns()
        return {"total_users_tracked": len(self._user_ips), "total_fingerprints": sum(len(h) for h in self._fingerprint_history.values()), "suspicious_users": len(suspicious), "high_risk_users": len([s for s in suspicious if s["risk_level"] == "high"])}

    def get_db_suspicious(self, db: Session, threshold=3):
        from sqlalchemy import func
        cutoff = datetime.utcnow() - timedelta(hours=24)
        results = db.query(UserActivity.user_id, func.count(func.distinct(UserActivity.user_ip)).label("unique_ips"), func.count(func.distinct(UserActivity.user_agent)).label("unique_uas")).filter(UserActivity.date_start >= cutoff).group_by(UserActivity.user_id).having(func.count(func.distinct(UserActivity.user_ip)) >= threshold).all()
        return [{"user_id": r.user_id, "unique_ips": r.unique_ips, "unique_user_agents": r.unique_uas, "risk_level": "high" if r.unique_ips > 10 else "medium"} for r in results]
