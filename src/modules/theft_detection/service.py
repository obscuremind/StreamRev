"""Theft detection service."""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set
from sqlalchemy.orm import Session
from src.core.logging.logger import logger
from src.domain.models import User, UserActivity

class TheftDetectionService:
    _connections: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    _alerts: List[Dict[str, Any]] = []
    _user_ips: Dict[int, Set[str]] = defaultdict(set)
    _user_agents: Dict[int, Set[str]] = defaultdict(set)

    def record_connection(self, user_id, ip, user_agent):
        now = datetime.utcnow()
        self._connections[user_id].append({"ip": ip, "user_agent": user_agent, "timestamp": now.isoformat()})
        self._user_ips[user_id].add(ip)
        self._user_agents[user_id].add(user_agent)
        if len(self._connections[user_id]) > 1000:
            self._connections[user_id] = self._connections[user_id][-500:]

    def detect_credential_sharing(self):
        results = []
        for uid, ips in self._user_ips.items():
            if len(ips) > 3:
                uas = self._user_agents.get(uid, set())
                results.append({"user_id": uid, "unique_ips": len(ips), "unique_user_agents": len(uas), "risk_level": "high" if len(ips) > 10 else "medium", "ips": list(ips), "user_agents": list(uas)[:10]})
        results.sort(key=lambda x: x["unique_ips"], reverse=True)
        return results

    def detect_redistribution(self):
        results = []
        cutoff = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
        for uid, events in self._connections.items():
            recent = [e for e in events if e["timestamp"] >= cutoff]
            recent_ips = {e["ip"] for e in recent}
            if len(recent_ips) > 5:
                results.append({"user_id": uid, "recent_connections": len(recent), "recent_unique_ips": len(recent_ips), "risk_level": "high", "note": "Possible stream redistribution"})
        return results

    def detect_credential_sharing_db(self, db: Session, threshold=3, hours=24):
        from sqlalchemy import func
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        results = db.query(UserActivity.user_id, func.count(func.distinct(UserActivity.user_ip)).label("unique_ips"), func.count(func.distinct(UserActivity.user_agent)).label("unique_uas"), func.count(UserActivity.id).label("total_conns")).filter(UserActivity.date_start >= cutoff).group_by(UserActivity.user_id).having(func.count(func.distinct(UserActivity.user_ip)) >= threshold).all()
        return [{"user_id": r.user_id, "unique_ips": r.unique_ips, "unique_user_agents": r.unique_uas, "total_connections": r.total_conns, "risk_level": "high" if r.unique_ips > 10 else "medium"} for r in results]

    def get_alerts(self):
        return list(self._alerts)

    def _add_alert(self, alert_type, user_id, message):
        self._alerts.append({"type": alert_type, "user_id": user_id, "message": message, "timestamp": datetime.utcnow().isoformat()})
        if len(self._alerts) > 500:
            self._alerts = self._alerts[-250:]

    def get_suspicious_users(self, threshold=3):
        results = []
        for uid, ips in self._user_ips.items():
            if len(ips) >= threshold:
                results.append({"user_id": uid, "unique_ips": len(ips), "unique_user_agents": len(self._user_agents.get(uid, set())), "total_connections": len(self._connections.get(uid, []))})
        results.sort(key=lambda x: x["unique_ips"], reverse=True)
        return results

    def auto_block(self, user_id, db: Session):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}
        user.enabled = False
        user.admin_notes = ((user.admin_notes or "") + f"\n[TheftDetection] Blocked {datetime.utcnow().isoformat()}").strip()
        db.commit()
        self._add_alert("user_blocked", user_id, f"User {user_id} auto-blocked")
        return {"success": True, "user_id": user_id, "blocked": True}

    def get_report(self, db: Session):
        sharing = self.detect_credential_sharing()
        redist = self.detect_redistribution()
        db_sharing = self.detect_credential_sharing_db(db)
        all_ids = {i["user_id"] for i in sharing + redist + db_sharing}
        return {"generated_at": datetime.utcnow().isoformat(), "total_tracked_users": len(self._user_ips), "credential_sharing_suspects": len(sharing), "redistribution_suspects": len(redist), "db_sharing_suspects": len(db_sharing), "total_unique_suspects": len(all_ids), "alerts": len(self._alerts), "credential_sharing": sharing[:20], "redistribution": redist[:20], "db_sharing": db_sharing[:20], "recent_alerts": self._alerts[-10:]}

    def get_stats(self):
        sharing = self.detect_credential_sharing()
        return {"total_tracked_users": len(self._user_ips), "total_connections_recorded": sum(len(v) for v in self._connections.values()), "suspicious_users": len(sharing), "high_risk_users": len([s for s in sharing if s["risk_level"] == "high"]), "active_alerts": len(self._alerts)}

    def clear_data(self):
        cc = sum(len(v) for v in self._connections.values())
        ac = len(self._alerts)
        self._connections.clear()
        self._user_ips.clear()
        self._user_agents.clear()
        self._alerts.clear()
        return {"connections_cleared": cc, "alerts_cleared": ac}
