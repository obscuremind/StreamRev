"""Shutdown handler for streaming sessions - ensures cleanup on disconnect/stop."""
import atexit
import os
import signal
from typing import Callable, List, Optional
from src.core.logging.logger import logger


class ShutdownHandler:
    def __init__(self):
        self._handlers: List[Callable] = []
        self._registered = False

    def register(self, handler: Callable):
        self._handlers.append(handler)
        if not self._registered:
            self._setup_signals()
            self._registered = True

    def _setup_signals(self):
        atexit.register(self._execute_all)
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, self._signal_handler)
            except (OSError, ValueError):
                pass

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, running shutdown handlers")
        self._execute_all()

    def _execute_all(self):
        for handler in reversed(self._handlers):
            try:
                handler()
            except Exception as e:
                logger.error(f"Shutdown handler error: {e}")
        self._handlers.clear()

    def cleanup_stream(self, stream_id: int, pid: Optional[int] = None, line_id: Optional[int] = None):
        logger.info(f"Cleaning up stream {stream_id} (PID: {pid}, Line: {line_id})")
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass


shutdown_handler = ShutdownHandler()
