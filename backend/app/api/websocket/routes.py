# app/api/websocket/routes.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.websocket.manager import ConnectionManager

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for live job updates"""

    await manager.connect(job_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or process commands if needed

    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
