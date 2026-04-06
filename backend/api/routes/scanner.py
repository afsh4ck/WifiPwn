from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.wifi_manager import wifi_manager

router = APIRouter()


class ScanRequest(BaseModel):
    interface: Optional[str] = None


@router.get("/networks")
async def get_networks():
    return wifi_manager.get_networks()


@router.post("/start")
async def start_scan(req: ScanRequest):
    iface = req.interface or wifi_manager.monitor_interface
    if not iface:
        raise HTTPException(status_code=400, detail="No hay interfaz seleccionada")

    # Auto-enable monitor mode if not already active
    monitor_enabled = False
    if not wifi_manager.is_monitor_mode(iface):
        ok, msg = wifi_manager.enable_monitor_mode(iface)
        if not ok:
            raise HTTPException(
                status_code=500,
                detail=f"No se pudo activar modo monitor en {iface}: {msg}"
            )
        iface = wifi_manager.monitor_interface  # may have been renamed
        monitor_enabled = True

    ok = wifi_manager.start_scan(iface)
    return {"success": ok, "interface": iface, "monitor_enabled": monitor_enabled}


@router.post("/stop")
async def stop_scan():
    ok = wifi_manager.stop_scan()
    return {"success": ok}


@router.get("/status")
async def scan_status():
    return {
        "scanning": wifi_manager._scanning,
        "networks_found": len(wifi_manager.get_networks()),
        "interface": wifi_manager.monitor_interface,
    }
