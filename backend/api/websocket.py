#!/usr/bin/env python3
"""
WifiPwn - WebSocket Connection Manager
Broadcast en tiempo real a todos los clientes conectados
"""

import json
import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# The main event loop — captured at startup so background threads can broadcast.
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def init_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Call once from the async lifespan to store the running event loop."""
    global _main_loop
    _main_loop = loop

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self._connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)

    async def broadcast(self, message: dict):
        payload = json.dumps(message, default=str)
        dead = []
        for ws in list(self._connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    # ------------------------------------------------------------------
    # Helpers para emitir tipos específicos de eventos
    # ------------------------------------------------------------------

    async def log(self, message: str, level: str = "info", source: str = "system"):
        await self.broadcast({
            "type": "log",
            "timestamp": datetime.now().isoformat(),
            "data": {"level": level, "message": message, "source": source},
        })

    async def scan_update(self, networks: list):
        await self.broadcast({
            "type": "scan_update",
            "timestamp": datetime.now().isoformat(),
            "data": {"networks": networks},
        })

    async def command_output(self, cmd_id: str, line: str):
        await self.broadcast({
            "type": "command_output",
            "timestamp": datetime.now().isoformat(),
            "data": {"cmd_id": cmd_id, "line": line},
        })

    async def status_update(self, key: str, value):
        await self.broadcast({
            "type": "status_update",
            "timestamp": datetime.now().isoformat(),
            "data": {"key": key, "value": value},
        })

    async def handshake_detected(self, bssid: str):
        await self.broadcast({
            "type": "handshake_detected",
            "timestamp": datetime.now().isoformat(),
            "data": {"bssid": bssid},
        })

    async def credential_captured(self, username: str, password: str):
        await self.broadcast({
            "type": "credential_captured",
            "timestamp": datetime.now().isoformat(),
            "data": {"username": username, "password": password},
        })

    @property
    def connected_count(self) -> int:
        return len(self._connections)


# Singleton global
manager = ConnectionManager()


# Helper para enviar desde código síncrono (threads) al loop asyncio
def broadcast_sync(message: dict):
    """Llama desde thread síncrono para emitir al WebSocket."""
    try:
        loop = _main_loop
        if loop is None:
            # Fallback: try to get the running loop (Python 3.10+)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), loop)
    except Exception:
        pass


def log_sync(message: str, level: str = "info", source: str = "system"):
    broadcast_sync({
        "type": "log",
        "timestamp": datetime.now().isoformat(),
        "data": {"level": level, "message": message, "source": source},
    })


def command_output_sync(cmd_id: str, line: str):
    broadcast_sync({
        "type": "command_output",
        "timestamp": datetime.now().isoformat(),
        "data": {"cmd_id": cmd_id, "line": line},
    })


def scan_update_sync(networks: list):
    broadcast_sync({
        "type": "scan_update",
        "timestamp": datetime.now().isoformat(),
        "data": {"networks": networks},
    })


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.log(f"Cliente conectado. Total: {manager.connected_count}", "info")
    try:
        while True:
            # Recibir ping/mensajes del cliente (keepalive)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        await manager.log(f"Cliente desconectado. Total: {manager.connected_count}", "info")
