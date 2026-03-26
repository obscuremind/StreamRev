import asyncio
from typing import Dict, List, Callable, Any
from src.core.logging.logger import logger


class EventDispatcher:
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, callback: Callable):
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable):
        if event_name in self._listeners:
            self._listeners[event_name] = [cb for cb in self._listeners[event_name] if cb != callback]

    async def dispatch(self, event_name: str, data: Any = None):
        if event_name not in self._listeners:
            return
        for callback in self._listeners[event_name]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Event handler error for '{event_name}': {e}")

    def get_listeners(self, event_name: str) -> List[Callable]:
        return self._listeners.get(event_name, [])


event_dispatcher = EventDispatcher()
