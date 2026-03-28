"""Watch folder service."""
import json, os
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.core.logging.logger import logger
from src.domain.models import Setting, Stream, Movie

MEDIA_EXTENSIONS = {".mp4", ".mkv", ".avi", ".ts", ".m3u8", ".flv", ".mov", ".wmv", ".mpg", ".mpeg"}

class WatchFolderService:
    def __init__(self, db: Session):
        self.db = db
        self._last_scan_results: List[Dict[str, Any]] = []

    def get_watch_dirs(self) -> List[str]:
        row = self.db.query(Setting).filter(Setting.key == "watch_directories").first()
        if row and row.value:
            try:
                return json.loads(row.value)
            except json.JSONDecodeError:
                pass
        return []

    def add_watch_dir(self, path: str) -> List[str]:
        dirs = self.get_watch_dirs()
        n = os.path.abspath(path)
        if n not in dirs:
            dirs.append(n)
            self._save(dirs)
        return dirs

    def remove_watch_dir(self, path: str) -> List[str]:
        dirs = self.get_watch_dirs()
        n = os.path.abspath(path)
        dirs = [d for d in dirs if d != n]
        self._save(dirs)
        return dirs

    def _save(self, dirs):
        row = self.db.query(Setting).filter(Setting.key == "watch_directories").first()
        val = json.dumps(dirs)
        if row:
            row.value = val
        else:
            row = Setting(key="watch_directories", value=val, value_type="json")
            self.db.add(row)
        self.db.commit()

    def scan_directory(self, path: str) -> List[Dict[str, Any]]:
        found = []
        if not os.path.isdir(path):
            return found
        for root, _d, files in os.walk(path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in MEDIA_EXTENSIONS:
                    fp = os.path.join(root, f)
                    try:
                        size = os.path.getsize(fp)
                    except OSError:
                        size = 0
                    found.append({"filename": f, "path": fp, "size": size, "extension": ext.lstrip("."), "directory": root})
        return found

    def scan_all(self) -> List[Dict[str, Any]]:
        results = []
        for d in self.get_watch_dirs():
            results.extend(self.scan_directory(d))
        self._last_scan_results = results
        return results

    def get_last_scan_results(self) -> List[Dict[str, Any]]:
        return self._last_scan_results

    def auto_import(self, path: str, category_id: Optional[int] = None, stream_type: str = "movie") -> Dict[str, Any]:
        files = self.scan_directory(path)
        imported = skipped = 0
        for f in files:
            name = os.path.splitext(f["filename"])[0]
            ext = f["extension"]
            if stream_type == "movie":
                if self.db.query(Movie).filter(Movie.stream_display_name == name).first():
                    skipped += 1; continue
                self.db.add(Movie(stream_display_name=name, stream_source=f["path"], category_id=category_id, container_extension=ext or "mkv", added=datetime.utcnow()))
            else:
                if self.db.query(Stream).filter(Stream.stream_display_name == name).first():
                    skipped += 1; continue
                self.db.add(Stream(stream_display_name=name, stream_source=json.dumps([f["path"]]), category_id=category_id, stream_type=1, enabled=True, added=datetime.utcnow()))
            imported += 1
        self.db.commit()
        return {"total_found": len(files), "imported": imported, "skipped": skipped}

    def import_files(self, file_paths: List[str], category_id: Optional[int] = None, stream_type: str = "movie") -> Dict[str, Any]:
        imported = skipped = 0
        for fp in file_paths:
            if not os.path.isfile(fp):
                skipped += 1; continue
            name = os.path.splitext(os.path.basename(fp))[0]
            ext = os.path.splitext(fp)[1].lstrip(".").lower()
            if stream_type == "movie":
                if self.db.query(Movie).filter(Movie.stream_display_name == name).first():
                    skipped += 1; continue
                self.db.add(Movie(stream_display_name=name, stream_source=fp, category_id=category_id, container_extension=ext or "mkv", added=datetime.utcnow()))
            else:
                if self.db.query(Stream).filter(Stream.stream_display_name == name).first():
                    skipped += 1; continue
                self.db.add(Stream(stream_display_name=name, stream_source=json.dumps([fp]), category_id=category_id, stream_type=1, enabled=True, added=datetime.utcnow()))
            imported += 1
        self.db.commit()
        return {"total": len(file_paths), "imported": imported, "skipped": skipped}
