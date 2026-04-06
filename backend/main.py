#!/usr/bin/env python3
"""WifiPwn - FastAPI Backend Entry Point"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.websocket import router as ws_router, manager, log_sync, scan_update_sync, command_output_sync, init_event_loop
from api.routes import dashboard, interfaces, scanner, handshake, cracking, deauth, evil_portal, campaigns
from core.wifi_manager import wifi_manager
from core.command_runner import command_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ─────────────────────────────────────────────────────────
    # Store the running event loop so background threads can broadcast via WS
    import asyncio
    init_event_loop(asyncio.get_event_loop())

    # Conectar callbacks del wifi_manager al WebSocket
    wifi_manager.on_log(lambda msg: log_sync(msg, "info", "wifi"))
    wifi_manager.on_scan_update(lambda nets: scan_update_sync(nets))
    wifi_manager.on_handshake(lambda bssid: log_sync(f"HANDSHAKE: {bssid}", "success", "capture"))

    # Streaming de output de comandos al WebSocket
    command_manager.subscribe_global(lambda cid, line: command_output_sync(cid, line))

    print("[*] WifiPwn API v2.0 iniciada en http://0.0.0.0:8000")
    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    command_manager.cancel_all()
    wifi_manager.cleanup()
    print("[*] WifiPwn API detenida")


app = FastAPI(
    title="WifiPwn API",
    description="WiFi Pentesting Tool - REST API v2",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket
app.include_router(ws_router)

# REST routes
app.include_router(dashboard.router,    prefix="/api/dashboard",   tags=["Dashboard"])
app.include_router(interfaces.router,   prefix="/api/interfaces",  tags=["Interfaces"])
app.include_router(scanner.router,      prefix="/api/scanner",     tags=["Scanner"])
app.include_router(handshake.router,    prefix="/api/handshake",   tags=["Handshake"])
app.include_router(cracking.router,     prefix="/api/cracking",    tags=["Cracking"])
app.include_router(deauth.router,       prefix="/api/deauth",      tags=["Deauth"])
app.include_router(evil_portal.router,  prefix="/api/evil-portal", tags=["Evil Portal"])
app.include_router(campaigns.router,    prefix="/api/campaigns",   tags=["Campaigns"])


@app.get("/api/health")
async def health():
    from core.utils import check_root_privileges
    return {
        "status": "ok",
        "version": "2.0.0",
        "root": check_root_privileges(),
        "ws_clients": manager.connected_count,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
