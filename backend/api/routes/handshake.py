from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pathlib import Path
from core.wifi_manager import wifi_manager
from core.database import db
from core.utils import validate_bssid, validate_channel, check_handshake_in_cap
from core.config import ConfigManager
from api.websocket import handshake_detected_sync

router = APIRouter()
config = ConfigManager()


class CaptureRequest(BaseModel):
    bssid: str
    channel: int
    essid: Optional[str] = None
    interface: Optional[str] = None
    output_file: Optional[str] = None
    auto_deauth: bool = False
    deauth_packets: int = 10


class CheckRequest(BaseModel):
    file: Optional[str] = None
    cap_file: Optional[str] = None  # alias for backwards compat
    bssid: Optional[str] = None

    @property
    def resolved_file(self) -> str:
        return self.file or self.cap_file or ""


@router.post("/start")
async def start_capture(req: CaptureRequest):
    if not validate_bssid(req.bssid):
        raise HTTPException(status_code=400, detail="BSSID inválido")
    if not validate_channel(req.channel):
        raise HTTPException(status_code=400, detail="Canal inválido")

    iface = req.interface or wifi_manager.monitor_interface
    if not iface:
        raise HTTPException(status_code=400, detail="No hay interfaz en modo monitor")

    out = req.output_file
    if not out:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = req.essid or req.bssid.replace(":", "")
        out = str(config.get_capture_path(f"{name}_{ts}"))

    def on_hs(bssid: str):
        # Emit WebSocket event immediately
        handshake_detected_sync(bssid)
        # Persist to DB
        net = db.get_network_by_bssid(bssid)
        if net:
            db.add_handshake(net["id"], out + "-01.cap")
        db.log_action("Handshake capturado", f"BSSID: {bssid}")
    ok = wifi_manager.start_capture(req.bssid, req.channel, out, iface, on_hs)
    if not ok:
        # If a stale capture is blocking, stop it and retry once
        wifi_manager.stop_capture()
        ok = wifi_manager.start_capture(req.bssid, req.channel, out, iface, on_hs)
    if not ok:
        raise HTTPException(status_code=500, detail="No se pudo iniciar la captura")

    if req.auto_deauth:
        wifi_manager.send_deauth(req.bssid, None, req.deauth_packets, iface)

    db.log_action("Captura iniciada", f"BSSID: {req.bssid} Canal: {req.channel}")
    return {"success": True, "output_prefix": out, "interface": iface}


@router.post("/stop")
async def stop_capture():
    ok = wifi_manager.stop_capture()
    return {"success": ok}


class DeauthRequest(BaseModel):
    bssid: str
    interface: Optional[str] = None
    client: Optional[str] = None
    count: int = 64


@router.post("/deauth")
async def send_deauth(req: DeauthRequest):
    if not validate_bssid(req.bssid):
        raise HTTPException(status_code=400, detail="BSSID inválido")
    iface = req.interface or wifi_manager.monitor_interface
    if not iface:
        raise HTTPException(status_code=400, detail="No hay interfaz disponible")
    ok = wifi_manager.send_deauth(req.bssid, req.client, req.count, iface)
    return {"success": ok}


@router.post("/check")
async def check_handshake(req: CheckRequest):
    found, msg = check_handshake_in_cap(req.resolved_file)
    return {"found": found, "message": msg}


@router.get("/list")
async def list_handshakes():
    return db.get_handshakes()


@router.get("/status")
async def capture_status():
    return {
        "capturing": wifi_manager._capturing,
        "interface": wifi_manager.monitor_interface,
    }
