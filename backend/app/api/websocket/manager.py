# app/api/websocket/manager.py

from fastapi import WebSocket
import logging
from typing import Dict, List

logger = logging.getLogger("satquery")


class ConnectionManager:
    """Manage WebSocket connections per job"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        logger.info(f"WebSocket connected for job {job_id}")

    async def broadcast(self, job_id: str, message: dict):
        """Send message to all clients watching job"""
        if job_id not in self.active_connections:
            return

        for websocket in self.active_connections[job_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                pass

    async def disconnect(self, job_id: str, websocket: WebSocket):
        """Remove disconnected client"""
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
            logger.info(f"WebSocket disconnected for job {job_id}")
