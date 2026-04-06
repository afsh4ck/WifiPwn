import os
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
from core.database import db
from core.wifi_manager import wifi_manager
from api.websocket import log_sync, broadcast_sync

router = APIRouter()

REPORTS_DIR = Path("/app/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Audit state ───────────────────────────────────────────────────────
_audit_state: dict = {"running": False, "campaign_id": None, "progress": [], "thread": None}


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class TargetFromNetwork(BaseModel):
    """Adds a network from the live scanner (upserts to DB first)."""
    bssid: str
    essid: Optional[str] = ""
    channel: Optional[int] = 0
    security: Optional[str] = ""
    cipher: Optional[str] = ""
    authentication: Optional[str] = ""
    power: Optional[int] = 0
    notes: Optional[str] = ""


class TechniquesUpdate(BaseModel):
    techniques: List[str]  # e.g. ["handshake", "deauth", "wps_scan"]


# ─── Campaigns ────────────────────────────────────────────────────────

@router.get("/")
async def list_campaigns():
    return db.get_campaigns()


@router.post("/")
async def create_campaign(req: CampaignCreate):
    cid = db.create_campaign(req.name, req.description)
    db.log_action("Campaña creada", req.name)
    return {"id": cid, "name": req.name}


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: int, req: CampaignUpdate):
    db.update_campaign(campaign_id, req.name, req.description, req.status)
    return {"success": True}


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int):
    db.delete_campaign(campaign_id)
    return {"success": True}


# ─── Targets ─────────────────────────────────────────────────────────

@router.get("/{campaign_id}/targets")
async def get_targets(campaign_id: int):
    return db.get_campaign_targets(campaign_id)


@router.post("/{campaign_id}/targets")
async def add_target_by_network(campaign_id: int, req: TargetFromNetwork):
    """Upsert the network to the DB and add it as a campaign target."""
    network_id = db.upsert_network(
        bssid=req.bssid, essid=req.essid, channel=req.channel,
        security=req.security, cipher=req.cipher,
        authentication=req.authentication, power=req.power,
    )
    db.add_campaign_target(campaign_id, network_id, req.notes or "")
    db.log_action("Objetivo añadido", f"Campaign {campaign_id} ← {req.bssid}")
    return {"success": True, "network_id": network_id}


@router.delete("/{campaign_id}/targets/{target_id}")
async def remove_target(campaign_id: int, target_id: int):
    with db.cursor() as cur:
        cur.execute("DELETE FROM campaign_targets WHERE id=? AND campaign_id=?",
                    (target_id, campaign_id))
    return {"success": True}


@router.put("/{campaign_id}/targets/{target_id}/techniques")
async def set_techniques(campaign_id: int, target_id: int, req: TechniquesUpdate):
    db.set_target_techniques(target_id, req.techniques)
    return {"success": True}


# ─── Auto-audit ───────────────────────────────────────────────────────

def _run_audit(campaign_id: int, targets: list):
    """Background thread: runs selected techniques against each target."""
    iface = wifi_manager.monitor_interface
    _audit_state["running"] = True
    _audit_state["campaign_id"] = campaign_id
    _audit_state["progress"] = []

    for t in targets:
        bssid = t.get("bssid")
        channel = t.get("channel") or 6
        essid = t.get("essid") or bssid
        target_id = t["id"]
        techniques = json.loads(t.get("techniques") or "[]")

        if not techniques:
            techniques = ["handshake", "deauth"]

        log_sync(f"[Audit] Iniciando → {essid} ({bssid})", "info", "campaign")
        db.update_target_status(target_id, "in_progress")
        result: dict = {"techniques": techniques, "findings": {}}

        try:
            if "deauth" in techniques and iface:
                wifi_manager.send_deauth(bssid, None, 3, iface)
                result["findings"]["deauth"] = "3 paquetes enviados"
                log_sync(f"[Audit] Deauth → {bssid}", "info", "campaign")
                time.sleep(2)

            if "handshake" in techniques and iface:
                cap_dir = Path("/app/captures")
                cap_dir.mkdir(exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                prefix = str(cap_dir / f"audit_{bssid.replace(':','')}")
                ok = wifi_manager.start_capture(bssid, channel, prefix, iface)
                if ok:
                    log_sync(f"[Audit] Capturando handshake de {bssid}...", "info", "campaign")
                    # Wait up to 60s for handshake
                    detected = threading.Event()
                    orig_cb = wifi_manager._capture_cb

                    def _hs_cb(b):
                        if b == bssid:
                            detected.set()
                    wifi_manager._capture_cb = _hs_cb

                    # Periodic deauth to force reconnection
                    for _ in range(6):
                        if detected.wait(timeout=10):
                            break
                        wifi_manager.send_deauth(bssid, None, 3, iface)

                    wifi_manager.stop_capture()
                    wifi_manager._capture_cb = orig_cb

                    if detected.is_set():
                        result["findings"]["handshake"] = "Capturado"
                        log_sync(f"[Audit] ✓ Handshake capturado de {bssid}", "success", "campaign")
                    else:
                        result["findings"]["handshake"] = "No capturado (timeout 60s)"

            if "wps_scan" in techniques:
                from core.utils import run_command
                rc, out, _ = run_command(["wash", "-i", iface or "wlan0", "-s"], timeout=20)
                result["findings"]["wps_scan"] = "WPS vulnerable" if bssid.upper() in out.upper() else "WPS no detectado"

        except Exception as e:
            result["error"] = str(e)
            log_sync(f"[Audit] Error en {bssid}: {e}", "error", "campaign")

        status = "completed" if not result.get("error") else "failed"
        db.update_target_status(target_id, status, result)
        _audit_state["progress"].append({"bssid": bssid, "status": status, "result": result})
        broadcast_sync({"type": "audit_progress", "timestamp": datetime.now().isoformat(),
                        "data": {"campaign_id": campaign_id, "bssid": bssid, "status": status}})

    _audit_state["running"] = False
    log_sync(f"[Audit] Campaña {campaign_id} completada", "success", "campaign")
    db.log_action("Auditoría completada", f"Campaign {campaign_id}")


@router.post("/{campaign_id}/audit/start")
async def start_audit(campaign_id: int):
    if _audit_state["running"]:
        raise HTTPException(400, "Ya hay una auditoría en curso")
    targets = db.get_campaign_targets(campaign_id)
    if not targets:
        raise HTTPException(400, "La campaña no tiene objetivos")
    t = threading.Thread(target=_run_audit, args=(campaign_id, targets), daemon=True)
    t.start()
    _audit_state["thread"] = t
    return {"success": True, "targets": len(targets)}


@router.get("/{campaign_id}/audit/status")
async def audit_status(campaign_id: int):
    return {
        "running": _audit_state["running"] and _audit_state["campaign_id"] == campaign_id,
        "progress": _audit_state["progress"],
    }


# ─── Reports ─────────────────────────────────────────────────────────

def _build_html_report(campaign: dict, targets: list, stats: dict) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    rows = ""
    for t in targets:
        techniques_raw = t.get("techniques") or "[]"
        try:
            techniques = ", ".join(json.loads(techniques_raw)) or "—"
        except Exception:
            techniques = techniques_raw
        result_raw = t.get("audit_result") or "{}"
        try:
            result = json.loads(result_raw)
            findings = result.get("findings", {})
            findings_str = "; ".join(f"{k}: {v}" for k, v in findings.items()) or "—"
        except Exception:
            findings_str = "—"
        status = t.get("audit_status", "pending")
        color = {"completed": "#16a34a", "failed": "#dc2626", "in_progress": "#f59e0b"}.get(status, "#6b7280")
        rows += f"""
        <tr>
          <td class="mono">{t.get('bssid','—')}</td>
          <td>{t.get('essid','—') or '(hidden)'}</td>
          <td>CH{t.get('channel','?')}</td>
          <td><span class="badge">{t.get('security','—')}</span></td>
          <td>{techniques}</td>
          <td style="color:{color};font-weight:700">{status.upper()}</td>
          <td class="findings">{findings_str}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Reporte — {campaign['name']}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#0d1117;color:#e6edf3;padding:40px 24px}}
.header{{background:linear-gradient(135deg,#1e3a5f 0%,#0d1117 100%);border:1px solid #30363d;border-radius:12px;padding:32px;margin-bottom:32px;display:flex;justify-content:space-between;align-items:flex-start}}
.header h1{{font-size:28px;font-weight:700;color:#58a6ff;margin-bottom:6px}}
.header p{{color:#8b949e;font-size:14px}}
.badge-status{{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;background:#21262d;color:#58a6ff;border:1px solid #388bfd}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:32px}}
.stat{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:20px;text-align:center}}
.stat .value{{font-size:36px;font-weight:700;color:#58a6ff}}
.stat .label{{font-size:12px;color:#8b949e;margin-top:4px;text-transform:uppercase;letter-spacing:.5px}}
.section{{background:#161b22;border:1px solid #30363d;border-radius:10px;margin-bottom:24px;overflow:hidden}}
.section-header{{background:#21262d;padding:16px 20px;font-size:14px;font-weight:600;color:#f0f6fc;border-bottom:1px solid #30363d}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;padding:10px 16px;color:#8b949e;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #21262d}}
td{{padding:12px 16px;border-bottom:1px solid #21262d;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:#1c2128}}
.mono{{font-family:monospace;font-size:12px;color:#58a6ff}}
.badge{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:#21262d;color:#79c0ff}}
.findings{{font-size:12px;color:#8b949e}}
.footer{{text-align:center;margin-top:32px;color:#484f58;font-size:12px}}
@media print{{body{{background:#fff;color:#000}}table td,table th{{color:#000}}.stat .value{{color:#1d4ed8}}}}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>📋 {campaign['name']}</h1>
    <p>{campaign.get('description') or 'Campaña de auditoría WiFi'}</p>
    <p style="margin-top:8px;font-size:12px;color:#6e7681">Generado: {now}</p>
  </div>
  <span class="badge-status">{campaign.get('status','active').upper()}</span>
</div>

<div class="stats">
  <div class="stat"><div class="value">{len(targets)}</div><div class="label">Objetivos</div></div>
  <div class="stat"><div class="value">{stats.get('total_handshakes',0)}</div><div class="label">Handshakes</div></div>
  <div class="stat"><div class="value">{stats.get('cracked_handshakes',0)}</div><div class="label">Contraseñas</div></div>
  <div class="stat"><div class="value">{stats.get('total_credentials',0)}</div><div class="label">Credenciales</div></div>
  <div class="stat"><div class="value">{sum(1 for t in targets if t.get('audit_status')=='completed')}</div><div class="label">Completados</div></div>
</div>

<div class="section">
  <div class="section-header">🎯 Objetivos auditados</div>
  <table>
    <thead><tr>
      <th>BSSID</th><th>ESSID</th><th>Canal</th><th>Seguridad</th>
      <th>Técnicas</th><th>Estado</th><th>Hallazgos</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>

<div class="footer">
  WifiPwn Audit Report · {now} · Solo para uso autorizado en pruebas de penetración
</div>
</body>
</html>"""


@router.post("/{campaign_id}/report")
async def generate_report(campaign_id: int):
    campaigns = db.get_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise HTTPException(404, "Campaña no encontrada")
    targets = db.get_campaign_targets(campaign_id)
    stats = db.get_statistics()
    html = _build_html_report(campaign, targets, stats)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in campaign["name"])
    filename = f"report_{safe_name}_{ts}.html"
    filepath = str(REPORTS_DIR / filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    size = os.path.getsize(filepath)
    rpt_id = db.save_report(campaign_id, filename, filepath, size)
    db.log_action("Reporte generado", f"Campaign {campaign_id}: {filename}")
    return {"id": rpt_id, "filename": filename, "size": size}


@router.get("/{campaign_id}/report")
async def get_report_legacy(campaign_id: int):
    """Legacy endpoint — returns JSON summary for backwards compat."""
    campaigns = db.get_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise HTTPException(404, "Campaña no encontrada")
    return {"campaign": campaign, "targets": db.get_campaign_targets(campaign_id), "stats": db.get_statistics()}


# ─── Reports management ───────────────────────────────────────────────

@router.get("/reports/all")
async def list_all_reports():
    return db.get_reports()


@router.get("/{campaign_id}/reports")
async def list_campaign_reports(campaign_id: int):
    return db.get_reports(campaign_id)


@router.get("/reports/{report_id}/download")
async def download_report(report_id: int):
    reports = db.get_reports()
    rpt = next((r for r in reports if r["id"] == report_id), None)
    if not rpt or not os.path.exists(rpt["filepath"]):
        raise HTTPException(404, "Reporte no encontrado")
    return FileResponse(rpt["filepath"], media_type="text/html",
                        headers={"Content-Disposition": f"attachment; filename={rpt['filename']}"})


@router.get("/reports/{report_id}/view")
async def view_report(report_id: int):
    reports = db.get_reports()
    rpt = next((r for r in reports if r["id"] == report_id), None)
    if not rpt or not os.path.exists(rpt["filepath"]):
        raise HTTPException(404, "Reporte no encontrado")
    content = Path(rpt["filepath"]).read_text(encoding="utf-8")
    return HTMLResponse(content)


@router.delete("/reports/{report_id}")
async def delete_report(report_id: int):
    filepath = db.delete_report(report_id)
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass
    return {"success": True}

