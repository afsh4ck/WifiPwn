# backend/core/utils.py
# Funciones auxiliares de WifiPwn (mismas que wifipwn/core/utils.py, sin PyQt5)

import re
import os
import subprocess
import shutil
import random
import tempfile
import logging
from typing import List, Tuple, Optional, Dict
from pathlib import Path


def check_root_privileges() -> bool:
    return os.geteuid() == 0 if hasattr(os, "geteuid") else False


def check_required_tools() -> List[str]:
    required = ["airmon-ng", "airodump-ng", "aireplay-ng", "aircrack-ng", "iw", "dnsmasq"]
    return [t for t in required if shutil.which(t) is None]


def validate_bssid(bssid: str) -> bool:
    return bool(re.match(r"^([0-9A-Fa-f]{2}[:\-]){5}([0-9A-Fa-f]{2})$", bssid))


def normalize_bssid(bssid: str) -> str:
    clean = bssid.replace(":", "").replace("-", "").upper()
    return ":".join(clean[i:i+2] for i in range(0, 12, 2))


def validate_channel(ch: int) -> bool:
    v2 = list(range(1, 15))
    v5 = [36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,144,149,153,157,161,165]
    return ch in v2 or ch in v5


def run_command(command: List[str], capture_output: bool = True,
                timeout: int = None, check: bool = False) -> Tuple[int, str, str]:
    try:
        r = subprocess.run(command, capture_output=capture_output, text=True,
                           timeout=timeout, check=check,
                           stdin=subprocess.DEVNULL)  # never block on stdin
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def kill_process(proc: subprocess.Popen) -> bool:
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        return True
    except Exception:
        return False


def get_wireless_interfaces() -> List[Dict]:
    """Detect all wireless interfaces regardless of driver model (nl80211 + WEXT)."""
    interfaces = []
    seen: set = set()

    # ── Method 1: iwconfig — universal, works for nl80211 AND WEXT/Realtek ──
    # wireless interfaces appear in stdout; non-wireless go to stderr
    try:
        _, stdout, _ = run_command(["iwconfig"])
        for line in stdout.split("\n"):
            # Interface sections start at column 0 (no leading whitespace)
            if line and not line[0].isspace() and line.strip():
                # Skip non-wireless entries (e.g. "lo  no wireless extensions.")
                if "no wireless extensions" in line.lower():
                    continue
                name = line.split()[0]
                if name and name not in seen:
                    interfaces.append({"name": name, "type": "managed", "channel": "", "txpower": ""})
                    seen.add(name)
    except Exception:
        pass

    # ── Method 2: iw dev — nl80211: augments existing entries with channel/type ──
    try:
        rc, stdout, _ = run_command(["iw", "dev"])
        if rc == 0:
            cur: Dict = {}
            for line in stdout.split("\n"):
                ls = line.strip()
                if ls.startswith("Interface "):
                    if cur and "name" in cur:
                        n = cur["name"]
                        if n in seen:
                            for iface in interfaces:
                                if iface["name"] == n:
                                    iface.update({k: v for k, v in cur.items() if v})
                                    break
                        else:
                            interfaces.append(cur)
                            seen.add(n)
                    cur = {"name": ls.split()[1], "type": "managed", "channel": "", "txpower": ""}
                elif cur:
                    if ls.startswith("type "):    cur["type"] = ls.split()[1]
                    elif ls.startswith("channel "): cur["channel"] = ls.split()[1]
                    elif ls.startswith("txpower "): cur["txpower"] = ls.split()[1]
            if cur and "name" in cur:
                n = cur["name"]
                if n in seen:
                    for iface in interfaces:
                        if iface["name"] == n:
                            iface.update({k: v for k, v in cur.items() if v})
                            break
                else:
                    interfaces.append(cur)
                    seen.add(n)
    except Exception:
        pass

    # ── Method 3: /proc/net/wireless — WEXT fallback ──────────────────
    try:
        with open("/proc/net/wireless") as f:
            for line in f.readlines()[2:]:
                name = line.split(":")[0].strip()
                if name and name not in seen:
                    interfaces.append({"name": name, "type": "managed", "channel": "", "txpower": ""})
                    seen.add(name)
    except Exception:
        pass

    # ── Method 4: /sys/class/net sysfs — last resort ──────────────────
    try:
        for iface in os.listdir("/sys/class/net"):
            if iface not in seen and os.path.exists(f"/sys/class/net/{iface}/wireless"):
                interfaces.append({"name": iface, "type": "unknown", "channel": "", "txpower": ""})
                seen.add(iface)
    except Exception:
        pass

    return interfaces


def get_interface_info(interface: str) -> Dict:
    info = {"name": interface, "mac": "", "mode": "unknown", "state": "unknown", "chipset": ""}
    try:
        # MAC from sysfs
        rc, stdout, _ = run_command(["cat", f"/sys/class/net/{interface}/address"])
        if rc == 0:
            info["mac"] = stdout.strip()

        # Mode: iwconfig first (works for WEXT/Realtek AND nl80211)
        rc2, out2, _ = run_command(["iwconfig", interface])
        if rc2 == 0 and out2.strip():
            m = re.search(r"Mode:(\S+)", out2)
            if m:
                info["mode"] = m.group(1).capitalize()

        # If iwconfig didn't give us a mode, try iw dev (nl80211)
        if info["mode"] == "unknown":
            rc3, out3, _ = run_command(["iw", "dev", interface, "info"])
            if rc3 == 0:
                for line in out3.split("\n"):
                    if line.strip().startswith("type "):
                        info["mode"] = line.strip().split()[1].capitalize()
                        break

        # Operstate
        rc, stdout, _ = run_command(["cat", f"/sys/class/net/{interface}/operstate"])
        if rc == 0:
            info["state"] = stdout.strip()
    except Exception:
        pass
    return info


def check_handshake_in_cap(cap_file: str, bssid: str = None) -> Tuple[bool, str]:
    """Check if a capture file contains a WPA handshake for the given BSSID.

    Takes a snapshot copy of the file first so we don't read a file that
    airodump-ng is actively writing to (avoids corrupt/partial reads).
    """
    if not os.path.exists(cap_file):
        return False, "Archivo no encontrado"

    try:
        fsize = os.path.getsize(cap_file)
        if fsize < 100:
            return False, "Archivo vacío — airodump aún no ha capturado paquetes"
    except Exception:
        pass

    # Take a snapshot copy so aircrack/tshark don't collide with airodump writes
    log = logging.getLogger("wifipwn.handshake")
    snap = None
    try:
        fd, snap = tempfile.mkstemp(suffix=".cap")
        os.close(fd)
        shutil.copy2(cap_file, snap)
    except Exception as e:
        log.warning("check_hs: no pude copiar %s: %s", cap_file, e)
        snap = cap_file  # fallback: read original

    try:
        return _check_hs_impl(snap, bssid, log)
    finally:
        if snap and snap != cap_file:
            try:
                os.unlink(snap)
            except Exception:
                pass


def _check_hs_impl(cap_file: str, bssid: Optional[str], log) -> Tuple[bool, str]:
    # ── Method 1: aircrack-ng ─────────────────────────────────────────
    try:
        cmd = ["aircrack-ng"]
        if bssid:
            cmd.extend(["-b", bssid])
        cmd.append(cap_file)
        rc, stdout, stderr = run_command(cmd, timeout=10)
        out = stdout + stderr
        log.debug("aircrack-ng rc=%d | %.300s", rc, out.replace("\n", " "))
        if re.search(r'\b[1-9]\d*\s+handshake', out, re.IGNORECASE):
            return True, "Handshake encontrado (aircrack-ng)"
    except Exception as e:
        log.warning("aircrack-ng error: %s", e)

    # ── Method 2: tshark EAPOL frame count ────────────────────────────
    try:
        filter_expr = "eapol"
        if bssid:
            bssid_lower = bssid.lower()
            filter_expr = f"eapol && (wlan.addr=={bssid_lower})"
        rc2, stdout2, stderr2 = run_command(
            ["tshark", "-r", cap_file, "-Y", filter_expr,
             "-T", "fields", "-e", "frame.number"],
            timeout=10,
        )
        log.debug("tshark rc=%d | frames=%s", rc2, stdout2.strip()[:100])
        if rc2 == 0 and stdout2.strip():
            frames = [l for l in stdout2.strip().split("\n") if l.strip()]
            if len(frames) >= 2:
                return True, f"Handshake ({len(frames)} frames EAPOL)"
    except Exception as e:
        log.warning("tshark error: %s", e)

    # ── Method 3: hcxpcapngtool ──────────────────────────────────────
    try:
        fd3, tmpf = tempfile.mkstemp(suffix=".hc22000")
        os.close(fd3)
        cmd3 = ["hcxpcapngtool", "-o", tmpf]
        # --filterlist_ap expects a FILE containing BSSIDs, one per line
        bssid_file = None
        if bssid:
            fd4, bssid_file = tempfile.mkstemp(suffix=".txt")
            os.close(fd4)
            with open(bssid_file, "w") as bf:
                # hcxpcapngtool wants BSSIDs without colons, lowercase
                bf.write(bssid.replace(":", "").lower() + "\n")
            cmd3.extend(["--filterlist_ap=" + bssid_file, "--filtermode=2"])
        cmd3.append(cap_file)
        rc3, stdout3, stderr3 = run_command(cmd3, timeout=10)
        out3 = stdout3 + stderr3
        log.debug("hcxpcapngtool rc=%d | %.200s", rc3, out3.replace("\n", " "))
        sz = 0
        try:
            sz = os.path.getsize(tmpf)
        except Exception:
            pass
        # Cleanup temp files
        for tf in (tmpf, bssid_file):
            if tf:
                try:
                    os.unlink(tf)
                except Exception:
                    pass
        if sz > 0:
            return True, "Handshake encontrado (hcxpcapngtool)"
    except Exception as e:
        log.warning("hcxpcapngtool error: %s", e)

    return False, "No se encontró handshake"


def generate_random_mac() -> str:
    mac = [0x02,
           random.randint(0, 0xFF),
           random.randint(0, 0xFF),
           random.randint(0, 0xFF),
           random.randint(0, 0xFF),
           random.randint(0, 0xFF)]
    return ":".join(f"{b:02x}" for b in mac)


def sanitize_filename(s: str) -> str:
    for ch in '<>:"/\\|?*':
        s = s.replace(ch, "_")
    return s.strip()[:255]


def parse_airodump_csv(csv_file: str) -> Tuple[List[Dict], List[Dict]]:
    aps, clients, section = [], [], "aps"
    try:
        with open(csv_file, "r", errors="ignore") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("BSSID"):
                continue
            if "Station MAC" in line:
                section = "clients"
                continue
            parts = [p.strip() for p in line.split(",")]
            if section == "aps" and len(parts) >= 14:
                def _int(v: str, default=0):
                    try: return int(v.strip())
                    except ValueError: return default
                aps.append({
                    "bssid":          parts[0].strip(),
                    "first_seen":     parts[1].strip(),
                    "last_seen":      parts[2].strip(),
                    "channel":        _int(parts[3]),
                    "speed":          _int(parts[4]),
                    "security":       parts[5].strip(),
                    "cipher":         parts[6].strip(),
                    "authentication": parts[7].strip(),
                    "power":          _int(parts[8]),
                    "beacons":        _int(parts[9]),
                    "ivs":            _int(parts[10]),
                    "essid":          parts[13].strip() if len(parts) > 13 else "",
                })
            elif section == "clients" and len(parts) >= 6:
                clients.append({
                    "station_mac": parts[0],
                    "power":       parts[3],
                    "bssid":       parts[5],
                })
    except Exception as e:
        print(f"Error parseando CSV: {e}")
    return aps, clients
