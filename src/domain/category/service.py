"""Stream / VOD category domain service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.models import StreamCategory


class CategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self, category_type: Optional[str] = None) -> List[StreamCategory]:
        query = self.db.query(StreamCategory)
        if category_type:
            query = query.filter(StreamCategory.category_type == category_type)
        return query.order_by(StreamCategory.order.asc(), StreamCategory.id.asc()).all()

    def get_by_id(self, cat_id: int) -> Optional[StreamCategory]:
        return (
            self.db.query(StreamCategory).filter(StreamCategory.id == cat_id).first()
        )

    def create(self, data: Dict[str, Any]) -> StreamCategory:
        cat = StreamCategory(**data)
        self.db.add(cat)
        self.db.commit()
        self.db.refresh(cat)
        return cat

    def update(self, cat_id: int, data: Dict[str, Any]) -> Optional[StreamCategory]:
        cat = self.get_by_id(cat_id)
        if not cat:
            return None
        for key, value in data.items():
            if hasattr(cat, key):
                setattr(cat, key, value)
        self.db.commit()
        self.db.refresh(cat)
        return cat

    def delete(self, cat_id: int) -> bool:
        cat = self.get_by_id(cat_id)
        if not cat:
            return False
        self.db.delete(cat)
        self.db.commit()
        return True

    def get_live_categories(self) -> List[StreamCategory]:
        return self.get_all(category_type="live")

    def get_movie_categories(self) -> List[StreamCategory]:
        return self.get_all(category_type="movie")

    def get_series_categories(self) -> List[StreamCategory]:
        return self.get_all(category_type="series")

    def get_radio_categories(self) -> List[StreamCategory]:
        return self.get_all(category_type="radio")
