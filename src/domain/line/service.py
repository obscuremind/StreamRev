"""Lines (active connections), packages, and resellers."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.core.auth.password import hash_password, verify_password
from src.domain.models import Line, Package, Reseller, UserActivity


class LineService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, line_id: int) -> Optional[Line]:
        return self.db.query(Line).filter(Line.id == line_id).first()

    def get_active_lines(
        self,
        user_id: Optional[int] = None,
        stream_id: Optional[int] = None,
        server_id: Optional[int] = None,
    ) -> List[Line]:
        query = self.db.query(Line)
        if user_id is not None:
            query = query.filter(Line.user_id == user_id)
        if stream_id is not None:
            query = query.filter(Line.stream_id == stream_id)
        if server_id is not None:
            query = query.filter(Line.server_id == server_id)
        return query.order_by(Line.date.desc()).all()

    def create_line(self, data: Dict[str, Any]) -> Line:
        line = Line(**data)
        self.db.add(line)
        self.db.commit()
        self.db.refresh(line)
        return line

    def remove_line(self, line_id: int) -> bool:
        line = self.get_by_id(line_id)
        if not line:
            return False
        self.db.delete(line)
        self.db.commit()
        return True

    def update_line(self, line_id: int, data: Dict[str, Any]) -> Optional[Line]:
        line = self.get_by_id(line_id)
        if not line:
            return None
        for key, value in data.items():
            if hasattr(line, key):
                setattr(line, key, value)
        self.db.commit()
        self.db.refresh(line)
        return line

    def remove_user_lines(self, user_id: int) -> int:
        count = self.db.query(Line).filter(Line.user_id == user_id).delete()
        self.db.commit()
        return count

    def log_activity(self, data: Dict[str, Any]) -> UserActivity:
        activity = UserActivity(**data)
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def get_online_count(self) -> int:
        return self.db.query(func.count(Line.id)).scalar() or 0

    def get_connection_count(self, user_id: int) -> int:
        return (
            self.db.query(func.count(Line.id)).filter(Line.user_id == user_id).scalar()
            or 0
        )


class PackageService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _encode_json_lists(data: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(data)
        for field in ("allowed_bouquets", "allowed_output_types"):
            if isinstance(out.get(field), list):
                out[field] = json.dumps(out[field])
        return out

    def get_all(self) -> List[Package]:
        return self.db.query(Package).order_by(Package.id.asc()).all()

    def get_by_id(self, package_id: int) -> Optional[Package]:
        return self.db.query(Package).filter(Package.id == package_id).first()

    def create(self, data: Dict[str, Any]) -> Package:
        payload = self._encode_json_lists(data)
        pkg = Package(**payload)
        self.db.add(pkg)
        self.db.commit()
        self.db.refresh(pkg)
        return pkg

    def update(self, package_id: int, data: Dict[str, Any]) -> Optional[Package]:
        pkg = self.get_by_id(package_id)
        if not pkg:
            return None
        payload = self._encode_json_lists(data)
        for key, value in payload.items():
            if hasattr(pkg, key):
                setattr(pkg, key, value)
        self.db.commit()
        self.db.refresh(pkg)
        return pkg

    def delete(self, package_id: int) -> bool:
        pkg = self.get_by_id(package_id)
        if not pkg:
            return False
        self.db.delete(pkg)
        self.db.commit()
        return True


class ResellerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        query = self.db.query(Reseller)
        total = query.count()
        items = (
            query.order_by(Reseller.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def get_by_id(self, reseller_id: int) -> Optional[Reseller]:
        return self.db.query(Reseller).filter(Reseller.id == reseller_id).first()

    def get_by_username(self, username: str) -> Optional[Reseller]:
        return self.db.query(Reseller).filter(Reseller.username == username).first()

    def authenticate(self, username: str, password: str) -> Optional[Reseller]:
        reseller = self.get_by_username(username)
        if not reseller:
            return None
        if not verify_password(password, reseller.password):
            return None
        if reseller.status != 1:
            return None
        return reseller

    def create(self, data: Dict[str, Any]) -> Reseller:
        payload = dict(data)
        if "password" in payload:
            payload["password"] = hash_password(payload["password"])
        reseller = Reseller(**payload)
        self.db.add(reseller)
        self.db.commit()
        self.db.refresh(reseller)
        return reseller

    def update(self, reseller_id: int, data: Dict[str, Any]) -> Optional[Reseller]:
        reseller = self.get_by_id(reseller_id)
        if not reseller:
            return None
        payload = dict(data)
        if payload.get("password"):
            payload["password"] = hash_password(payload["password"])
        else:
            payload.pop("password", None)
        for key, value in payload.items():
            if hasattr(reseller, key):
                setattr(reseller, key, value)
        self.db.commit()
        self.db.refresh(reseller)
        return reseller

    def delete(self, reseller_id: int) -> bool:
        reseller = self.get_by_id(reseller_id)
        if not reseller:
            return False
        self.db.delete(reseller)
        self.db.commit()
        return True

    def add_credits(self, reseller_id: int, amount: int) -> Optional[Reseller]:
        reseller = self.get_by_id(reseller_id)
        if not reseller or amount < 0:
            return None
        if reseller.max_credits is not None:
            if reseller.credits + amount > reseller.max_credits:
                return None
        reseller.credits += amount
        self.db.commit()
        self.db.refresh(reseller)
        return reseller

    def use_credits(self, reseller_id: int, amount: int) -> bool:
        reseller = self.get_by_id(reseller_id)
        if not reseller or amount < 0 or reseller.credits < amount:
            return False
        reseller.credits -= amount
        self.db.commit()
        return True

    def set_credits(self, reseller_id: int, credits: int) -> Optional[Reseller]:
        reseller = self.get_by_id(reseller_id)
        if not reseller or credits < 0:
            return None
        if reseller.max_credits is not None and credits > reseller.max_credits:
            return None
        reseller.credits = credits
        self.db.commit()
        self.db.refresh(reseller)
        return reseller

    def get_stats(self) -> Dict[str, int]:
        return {
            "total": self.db.query(func.count(Reseller.id)).scalar() or 0,
            "enabled": self.db.query(func.count(Reseller.id))
            .filter(Reseller.status == 1)
            .scalar()
            or 0,
            "disabled": self.db.query(func.count(Reseller.id))
            .filter(Reseller.status == 0)
            .scalar()
            or 0,
        }
