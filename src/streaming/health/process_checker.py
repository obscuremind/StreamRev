"""Process health checker for streaming engine."""
import psutil
from typing import Dict, List, Optional
from src.core.logging.logger import logger


class ProcessChecker:
    @staticmethod
    def is_pid_alive(pid: int) -> bool:
        try:
            return psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    @staticmethod
    def get_process_info(pid: int) -> Optional[Dict]:
        try:
            proc = psutil.Process(pid)
            return {
                "pid": pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(),
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                "create_time": proc.create_time(),
                "cmdline": " ".join(proc.cmdline())[:500],
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    @staticmethod
    def find_ffmpeg_processes() -> List[Dict]:
        result = []
        for proc in psutil.process_iter(["pid", "name", "cmdline", "cpu_percent", "memory_info"]):
            try:
                if "ffmpeg" in (proc.info["name"] or "").lower():
                    result.append({
                        "pid": proc.info["pid"],
                        "name": proc.info["name"],
                        "cpu_percent": proc.info["cpu_percent"],
                        "memory_mb": proc.info["memory_info"].rss / 1024 / 1024 if proc.info["memory_info"] else 0,
                        "cmdline": " ".join(proc.info["cmdline"] or [])[:500],
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return result

    @staticmethod
    def check_multiple_pids(pids: List[int]) -> Dict[int, bool]:
        return {pid: ProcessChecker.is_pid_alive(pid) for pid in pids}

    @staticmethod
    def get_ffmpeg_count() -> int:
        return len(ProcessChecker.find_ffmpeg_processes())

    @staticmethod
    def kill_orphaned_ffmpeg(known_pids: set) -> int:
        killed = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if "ffmpeg" in (proc.info["name"] or "").lower() and proc.info["pid"] not in known_pids:
                    proc.terminate()
                    killed += 1
                    logger.warning(f"Killed orphaned FFmpeg process {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return killed


process_checker = ProcessChecker()
