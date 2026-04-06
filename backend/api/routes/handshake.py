from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
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

    # Auto-enable monitor mode if needed
    from core.utils import get_interface_info
    info = get_interface_info(iface)
    if info.get("mode", "").lower() != "monitor":
        ok_mon, msg = wifi_manager.enable_monitor_mode(iface)
        if not ok_mon:
            raise HTTPException(status_code=500, detail=f"No se pudo activar monitor: {msg}")
        iface = wifi_manager.monitor_interface or iface

    out = req.output_file
    if not out:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = req.essid or req.bssid.replace(":", "")
        out = str(config.get_capture_path(f"{name}_{ts}"))

    def on_hs(bssid: str):
        # NOTE: global callback in main.py already broadcasts handshake_detected_sync,
        # so we do NOT call it again here to avoid duplicate WS messages.
        # Persist to DB — find actual .cap file
        cap = wifi_manager._find_cap_file(out) or (out + "-01.cap")
        net = db.get_network_by_bssid(bssid)
        if not net:
            # Network may not be in DB yet (manual BSSID entry, etc.) — create it
            nid = db.upsert_network(bssid)
            net = {"id": nid}
        db.add_handshake(net["id"], cap)
        db.log_action("Handshake capturado", f"BSSID: {bssid} → {cap}")
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
    # Auto-enable monitor mode if needed
    from core.utils import get_interface_info as _info
    if _info(iface).get("mode", "").lower() != "monitor":
        ok_mon, _ = wifi_manager.enable_monitor_mode(iface)
        if ok_mon:
            iface = wifi_manager.monitor_interface or iface
    ok = wifi_manager.send_deauth(req.bssid, req.client, req.count, iface)
    return {"success": ok}


@router.post("/check")
async def check_handshake(req: CheckRequest):
    found, msg = check_handshake_in_cap(req.resolved_file, req.bssid)
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


@router.get("/download/{handshake_id}")
async def download_handshake(handshake_id: int):
    """Download a captured handshake .pcap file."""
    hs_list = db.get_handshakes()
    hs = next((h for h in hs_list if h["id"] == handshake_id), None)
    if not hs:
        raise HTTPException(status_code=404, detail="Handshake no encontrado")
    cap_path = Path(hs["capture_file"])
    if not cap_path.exists():
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {hs['capture_file']}")
    filename = cap_path.name
    return FileResponse(
        path=str(cap_path),
        media_type="application/octet-stream",
        filename=filename,
    )
