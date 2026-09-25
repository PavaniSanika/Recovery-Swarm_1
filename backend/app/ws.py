"""WebSocket Manager for RECOVERY-SWARM (Stage E).

Manages active connections per patient and streams typed real-time events.
"""

import asyncio
import json
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        # Map patient_id -> active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, patient_id: str):
        await websocket.accept()
        if patient_id not in self.active_connections:
            self.active_connections[patient_id] = set()
        self.active_connections[patient_id].add(websocket)

    def disconnect(self, websocket: WebSocket, patient_id: str):
        if patient_id in self.active_connections:
            self.active_connections[patient_id].discard(websocket)
            if not self.active_connections[patient_id]:
                del self.active_connections[patient_id]

    async def broadcast(self, patient_id: str, message_type: str, payload: dict):
        """Broadcasts a typed WsMessage event to all connected clients for patient_id."""
        if patient_id not in self.active_connections:
            return

        ws_msg = {
            "type": message_type,
            "payload": payload,
        }

        dead_sockets = set()
        for websocket in list(self.active_connections[patient_id]):
            try:
                await websocket.send_json(ws_msg)
            except Exception:
                dead_sockets.add(websocket)

        for ws in dead_sockets:
            self.disconnect(ws, patient_id)


# Global connection manager instance
ws_manager = ConnectionManager()
