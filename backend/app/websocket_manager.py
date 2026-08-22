from typing import Dict, Set
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set] = {}  # key: "session_id_topic_id"

    def _get_key(self, session_id: int, topic_id: int) -> str:
        return f"{session_id}_{topic_id}"

    async def connect(self, websocket, session_id: int, topic_id: int):
        await websocket.accept()
        key = self._get_key(session_id, topic_id)
        if key not in self.active_connections:
            self.active_connections[key] = set()
        self.active_connections[key].add(websocket)

    def disconnect(self, websocket, session_id: int, topic_id: int):
        key = self._get_key(session_id, topic_id)
        if key in self.active_connections:
            self.active_connections[key].discard(websocket)
            if not self.active_connections[key]:
                del self.active_connections[key]

    async def send_message(self, session_id: int, topic_id: int, message: dict):
        key = self._get_key(session_id, topic_id)
        if key in self.active_connections:
            for ws in self.active_connections[key]:
                try:
                    await ws.send_text(json.dumps(message, ensure_ascii=False))
                except Exception as e:
                    print(f"发送消息失败: {e}")

manager = ConnectionManager()