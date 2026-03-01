from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast(self, message: dict):
        for user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)


manager = ConnectionManager()

NOTIFICATION_TYPES = {
    "exam_result": "Exam results are available",
    "achievement": "New achievement unlocked!",
    "journal_reminder": "Time for journal reflection",
    "profile_update": "Your profile has been updated",
}


async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


async def send_notification(user_id: str, notification_type: str, data: dict = None):
    message = {
        "type": notification_type,
        "message": NOTIFICATION_TYPES.get(notification_type, "Notification"),
        "data": data or {},
        "timestamp": asyncio.get_event_loop().time(),
    }
    await manager.send_personal_message(message, user_id)


async def broadcast_notification(notification_type: str, data: dict = None):
    message = {
        "type": notification_type,
        "message": NOTIFICATION_TYPES.get(notification_type, "Notification"),
        "data": data or {},
    }
    await manager.broadcast(message)
