"""Stream provider management - external IPTV source providers."""

import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.models import Stream


class ProviderService:
    def __init__(self, db: Session):
        self.db = db

    def get_providers(self) -> List[Dict[str, Any]]:
        streams = self.db.query(Stream).all()
        providers = {}
        for s in streams:
            sources = self._parse_sources(s.stream_source)
            for src in sources:
                domain = self._extract_domain(src)
                if domain:
                    if domain not in providers:
                        providers[domain] = {"domain": domain, "stream_count": 0, "streams": []}
                    providers[domain]["stream_count"] += 1
                    providers[domain]["streams"].append(s.id)
        return list(providers.values())

    def get_streams_by_provider(self, domain: str) -> List[Stream]:
        streams = self.db.query(Stream).all()
        result = []
        for s in streams:
            sources = self._parse_sources(s.stream_source)
            for src in sources:
                if domain in src:
                    result.append(s)
                    break
        return result

    @staticmethod
    def _parse_sources(source_str: str) -> List[str]:
        if not source_str:
            return []
        try:
            parsed = json.loads(source_str)
            return parsed if isinstance(parsed, list) else [str(parsed)]
        except (json.JSONDecodeError, TypeError):
            return [source_str]

    @staticmethod
    def _extract_domain(url: str) -> Optional[str]:
        match = re.match(r"https?://([^/:]+)", url)
        return match.group(1) if match else None
