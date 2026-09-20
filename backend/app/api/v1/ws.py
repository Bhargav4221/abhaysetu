from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.ws.hub import ws_hub

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None):
    payload = decode_token(token) if token else None
    if not payload:
        await websocket.close(code=4401)
        return
    await ws_hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_hub.disconnect(websocket)
