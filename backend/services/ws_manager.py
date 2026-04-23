from __future__ import annotations
import asyncio
import json
import logging
from typing import Any
from fastapi import WebSocket

log = logging.getLogger(__name__)


class WSManager:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self.clients.discard(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        data = json.dumps(message, default=str)
        async with self._lock:
            clients = list(self.clients)
        if not clients:
            return
        results = await asyncio.gather(
            *(c.send_text(data) for c in clients), return_exceptions=True
        )
        dead = [c for c, r in zip(clients, results) if isinstance(r, Exception)]
        if dead:
            async with self._lock:
                for c in dead:
                    self.clients.discard(c)


ws_manager = WSManager()
