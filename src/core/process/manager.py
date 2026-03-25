import os
import signal
import subprocess
from typing import Optional, Dict, List
import psutil
from src.core.logging.logger import logger


class ProcessManager:
    def __init__(self):
        self._processes: Dict[str, subprocess.Popen] = {}

    def start(self, name: str, command: List[str], cwd: Optional[str] = None, env: Optional[dict] = None) -> Optional[int]:
        try:
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
            )
            self._processes[name] = proc
            logger.info(f"Started process '{name}' with PID {proc.pid}")
            return proc.pid
        except Exception as e:
            logger.error(f"Failed to start process '{name}': {e}")
            return None

    def stop(self, name: str, timeout: int = 10) -> bool:
        proc = self._processes.get(name)
        if not proc:
            return False
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=timeout)
            del self._processes[name]
            logger.info(f"Stopped process '{name}'")
            return True
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()
            del self._processes[name]
            logger.warning(f"Force-killed process '{name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to stop process '{name}': {e}")
            return False

    def kill_by_pid(self, pid: int) -> bool:
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except ProcessLookupError:
            return False
        except Exception as e:
            logger.error(f"Failed to kill PID {pid}: {e}")
            return False

    def is_running(self, name: str) -> bool:
        proc = self._processes.get(name)
        if not proc:
            return False
        return proc.poll() is None

    def get_pid(self, name: str) -> Optional[int]:
        proc = self._processes.get(name)
        if proc and proc.poll() is None:
            return proc.pid
        return None

    @staticmethod
    def get_system_info() -> dict:
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "cpu_count": psutil.cpu_count(),
            "memory": dict(psutil.virtual_memory()._asdict()),
            "disk": dict(psutil.disk_usage("/")._asdict()),
            "network": {k: dict(v._asdict()) for k, v in psutil.net_io_counters(pernic=True).items()},
            "uptime": int(psutil.boot_time()),
        }

    def list_processes(self) -> Dict[str, dict]:
        result = {}
        for name, proc in self._processes.items():
            result[name] = {
                "pid": proc.pid,
                "running": proc.poll() is None,
                "returncode": proc.returncode,
            }
        return result

    def cleanup(self):
        for name in list(self._processes.keys()):
            self.stop(name)


process_manager = ProcessManager()
