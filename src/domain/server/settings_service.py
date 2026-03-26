"""Typed key-value settings backed by `Setting` rows."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.models import Setting


class SettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._cache: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._cache:
            return self._cache[key]
        row = self.db.query(Setting).filter(Setting.key == key).first()
        if not row:
            return default
        value = self._cast_value(row.value or "", row.value_type)
        self._cache[key] = value
        return value

    def set(self, key: str, value: Any, value_type: str = "string") -> Setting:
        row = self.db.query(Setting).filter(Setting.key == key).first()
        if value_type == "json":
            str_value = json.dumps(value)
        elif value_type == "bool":
            str_value = "true" if bool(value) else "false"
        else:
            str_value = "" if value is None else str(value)
        if row:
            row.value = str_value
            row.value_type = value_type
        else:
            row = Setting(key=key, value=str_value, value_type=value_type)
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        self._cache[key] = self._cast_value(str_value, value_type)
        return row

    def delete(self, key: str) -> bool:
        count = self.db.query(Setting).filter(Setting.key == key).delete()
        self.db.commit()
        self._cache.pop(key, None)
        return count > 0

    def get_all(self) -> Dict[str, Any]:
        rows = self.db.query(Setting).order_by(Setting.key.asc()).all()
        return {r.key: self._cast_value(r.value or "", r.value_type) for r in rows}

    def clear_cache(self) -> None:
        self._cache.clear()

    def list_rows(self) -> List[Setting]:
        return self.db.query(Setting).order_by(Setting.key.asc()).all()

    def get_row_by_id(self, row_id: int) -> Optional[Setting]:
        return self.db.query(Setting).filter(Setting.id == row_id).first()

    def create_row(self, key: str, value: Any, value_type: str = "string") -> Setting:
        return self.set(key, value, value_type)

    def update_row(self, row_id: int, data: Dict[str, Any]) -> Optional[Setting]:
        row = self.get_row_by_id(row_id)
        if not row:
            return None
        old_key = row.key
        payload = dict(data)
        if "key" in payload:
            row.key = payload["key"]
        if "value_type" in payload:
            row.value_type = payload["value_type"]
        if "value" in payload:
            vt = row.value_type
            val = payload["value"]
            if vt == "json":
                row.value = json.dumps(val)
            elif vt == "bool":
                row.value = "true" if bool(val) else "false"
            else:
                row.value = "" if val is None else str(val)
        self.db.commit()
        self.db.refresh(row)
        self._cache.pop(old_key, None)
        self._cache.pop(row.key, None)
        return row

    def delete_row_by_id(self, row_id: int) -> bool:
        row = self.get_row_by_id(row_id)
        if not row:
            return False
        k = row.key
        self.db.delete(row)
        self.db.commit()
        self._cache.pop(k, None)
        return True

    @staticmethod
    def _cast_value(value: str, value_type: str) -> Any:
        if value_type == "int":
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
        if value_type == "bool":
            return value.lower() in ("true", "1", "yes", "on") if value else False
        if value_type == "json":
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value
