"""Signal sender - sends control signals to FFmpeg and other streaming processes."""
import os
import signal
from typing import Optional
from src.core.config import settings
from src.core.logging.logger import logger


class SignalSender:
    def __init__(self):
        self.signals_dir = os.path.join(settings.BASE_DIR, "signals")

    def send_signal(self, pid: int, sig: int = signal.SIGTERM) -> bool:
        try:
            os.kill(pid, sig)
            logger.info(f"Sent signal {sig} to PID {pid}")
            return True
        except ProcessLookupError:
            logger.warning(f"Process {pid} not found")
            return False
        except PermissionError:
            logger.error(f"Permission denied sending signal to PID {pid}")
            return False

    def send_stop(self, pid: int) -> bool:
        return self.send_signal(pid, signal.SIGTERM)

    def send_kill(self, pid: int) -> bool:
        return self.send_signal(pid, signal.SIGKILL)

    def send_hup(self, pid: int) -> bool:
        return self.send_signal(pid, signal.SIGHUP)

    def write_signal_file(self, name: str, content: str = "1") -> bool:
        os.makedirs(self.signals_dir, exist_ok=True)
        sig_path = os.path.join(self.signals_dir, name)
        try:
            with open(sig_path, "w") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to write signal file {name}: {e}")
            return False

    def read_signal_file(self, name: str) -> Optional[str]:
        sig_path = os.path.join(self.signals_dir, name)
        if os.path.exists(sig_path):
            with open(sig_path, "r") as f:
                content = f.read()
            os.remove(sig_path)
            return content
        return None

    def check_signal(self, name: str) -> bool:
        sig_path = os.path.join(self.signals_dir, name)
        if os.path.exists(sig_path):
            os.remove(sig_path)
            return True
        return False

    def clear_all_signals(self):
        if os.path.exists(self.signals_dir):
            for f in os.listdir(self.signals_dir):
                os.remove(os.path.join(self.signals_dir, f))


signal_sender = SignalSender()
