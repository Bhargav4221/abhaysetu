from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket

from app.core.redis import publish


class Hub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event, default=str)
        await publish("abhaysetu.events", payload)
        stale: list[WebSocket] = []
        async with self._lock:
            clients = list(self._clients)
        for client in clients:
            try:
                await client.send_text(payload)
            except Exception:  # noqa: BLE001
                stale.append(client)
        for client in stale:
            await self.disconnect(client)


ws_hub = Hub()
