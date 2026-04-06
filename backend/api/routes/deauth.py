from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.wifi_manager import wifi_manager
from core.database import db
from core.utils import validate_bssid

router = APIRouter()


class DeauthRequest(BaseModel):
    bssid: str
    client: Optional[str] = None
    packets: int = 10
    interface: Optional[str] = None


@router.post("/send")
async def send_deauth(req: DeauthRequest):
    if not validate_bssid(req.bssid):
        raise HTTPException(status_code=400, detail="BSSID inválido")
    if req.client and not validate_bssid(req.client):
        raise HTTPException(status_code=400, detail="MAC cliente inválida")

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

    ok = wifi_manager.send_deauth(req.bssid, req.client, req.packets, iface)
    if not ok:
        raise HTTPException(status_code=500, detail="No se pudo enviar deauth")

    net = db.get_network_by_bssid(req.bssid)
    if net:
        db.log_deauth(net["id"], req.client, req.packets)

    db.log_action("Deauth enviado", f"AP: {req.bssid} Cliente: {req.client or 'broadcast'} Pkts: {req.packets}")
    return {"success": True, "packets": req.packets, "target": req.client or "broadcast"}


@router.post("/stop")
async def stop_deauth():
    ok = wifi_manager.stop_deauth()
    return {"success": ok}


@router.get("/history")
async def deauth_history():
    with db.cursor() as cur:
        cur.execute("""
            SELECT d.*, n.bssid as ap_bssid, n.essid
            FROM deauth_attacks d
            LEFT JOIN networks n ON d.network_id=n.id
            ORDER BY d.attack_date DESC LIMIT 100
        """)
        return [dict(r) for r in cur.fetchall()]
