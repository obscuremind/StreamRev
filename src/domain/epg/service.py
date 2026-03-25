"""EPG domain service: programmes, XMLTV import, cleanup, stats."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.models import EpgData


def _local_tag(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _parse_xmltv_datetime(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    s = raw.strip()
    if len(s) < 14:
        return None
    try:
        return datetime.strptime(s[:14], "%Y%m%d%H%M%S")
    except ValueError:
        return None


class EpgService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_current_program(self, channel_id: str) -> Optional[EpgData]:
        now = datetime.utcnow()
        return (
            self.db.query(EpgData)
            .filter(
                EpgData.epg_id == channel_id,
                EpgData.start <= now,
                EpgData.end >= now,
            )
            .order_by(EpgData.start.desc())
            .first()
        )

    def get_programs(self, channel_id: str, limit: int = 20) -> List[EpgData]:
        now = datetime.utcnow()
        return (
            self.db.query(EpgData)
            .filter(EpgData.epg_id == channel_id, EpgData.end >= now)
            .order_by(EpgData.start.asc())
            .limit(limit)
            .all()
        )

    def get_all_programs(self, channel_id: str) -> List[EpgData]:
        """All EPG rows for a channel id (epg_id), ordered by start time (e.g. XMLTV export)."""
        return (
            self.db.query(EpgData)
            .filter(EpgData.epg_id == channel_id)
            .order_by(EpgData.start.asc())
            .all()
        )

    def import_xmltv(self, xml_content: str) -> int:
        count = 0
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return 0

        for elem in root.iter():
            if _local_tag(elem.tag) != "programme":
                continue
            ch = elem.get("channel") or ""
            start = _parse_xmltv_datetime(elem.get("start") or "")
            end = _parse_xmltv_datetime(elem.get("stop") or "")
            if start is None or end is None:
                continue
            title_el = desc_el = None
            for child in elem:
                ln = _local_tag(child.tag)
                if ln == "title" and title_el is None:
                    title_el = child
                elif ln == "desc" and desc_el is None:
                    desc_el = child
            title = (
                (title_el.text or "").strip()
                if title_el is not None and title_el.text
                else ""
            )
            description = (
                (desc_el.text or "").strip()
                if desc_el is not None and desc_el.text
                else None
            )
            lang = (
                title_el.get("lang", "en")
                if title_el is not None
                else "en"
            )
            self.db.add(
                EpgData(
                    epg_id=ch,
                    title=title,
                    lang=lang,
                    start=start,
                    end=end,
                    description=description,
                )
            )
            count += 1
            if count % 500 == 0:
                self.db.flush()

        self.db.commit()
        return count

    def clear_old(self, days: int = 7) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        count = self.db.query(EpgData).filter(EpgData.end < cutoff).delete()
        self.db.commit()
        return count

    def clear_all(self) -> int:
        count = self.db.query(EpgData).delete()
        self.db.commit()
        return count

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_programs": self.db.query(func.count(EpgData.id)).scalar() or 0,
            "channels": self.db.query(func.count(func.distinct(EpgData.epg_id))).scalar()
            or 0,
        }

    def list_programs(
        self,
        epg_id: Optional[str] = None,
        channel_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict[str, Any]:
        query = self.db.query(EpgData)
        if epg_id is not None:
            query = query.filter(EpgData.epg_id == epg_id)
        if channel_id is not None:
            query = query.filter(EpgData.channel_id == channel_id)
        total = query.count()
        items = (
            query.order_by(EpgData.start.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {"items": items, "total": total, "page": page, "per_page": per_page}

    def get_program_by_id(self, program_id: int) -> Optional[EpgData]:
        return self.db.query(EpgData).filter(EpgData.id == program_id).first()

    def create_program(self, data: Dict[str, Any]) -> EpgData:
        row = EpgData(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_program(
        self, program_id: int, data: Dict[str, Any]
    ) -> Optional[EpgData]:
        row = self.get_program_by_id(program_id)
        if not row:
            return None
        for key, value in data.items():
            if hasattr(row, key):
                setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_program(self, program_id: int) -> bool:
        row = self.get_program_by_id(program_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True
