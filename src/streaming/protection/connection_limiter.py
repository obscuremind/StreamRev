from typing import Dict, Set


class ConnectionLimiter:
    def __init__(self):
        self._connections: Dict[int, Set[str]] = {}

    def add_connection(self, user_id: int, connection_id: str) -> bool:
        if user_id not in self._connections:
            self._connections[user_id] = set()
        self._connections[user_id].add(connection_id)
        return True

    def remove_connection(self, user_id: int, connection_id: str):
        if user_id in self._connections:
            self._connections[user_id].discard(connection_id)
            if not self._connections[user_id]:
                del self._connections[user_id]

    def get_count(self, user_id: int) -> int:
        return len(self._connections.get(user_id, set()))

    def can_connect(self, user_id: int, max_connections: int) -> bool:
        return self.get_count(user_id) < max_connections

    def get_all(self) -> Dict[int, int]:
        return {uid: len(conns) for uid, conns in self._connections.items()}

    def clear_user(self, user_id: int):
        self._connections.pop(user_id, None)


connection_limiter = ConnectionLimiter()
