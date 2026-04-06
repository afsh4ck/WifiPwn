# backend/core/utils.py
# Funciones auxiliares de WifiPwn (mismas que wifipwn/core/utils.py, sin PyQt5)

import re
import os
import subprocess
import shutil
import random
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
                           timeout=timeout, check=check)
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
    interfaces = []
    seen: set = set()

    # Method 1: iw dev — nl80211 drivers
    try:
        rc, stdout, _ = run_command(["iw", "dev"])
        if rc == 0:
            cur: Dict = {}
            for line in stdout.split("\n"):
                line = line.strip()
                if line.startswith("Interface "):
                    if cur:
                        interfaces.append(cur)
                        seen.add(cur["name"])
                    cur = {"name": line.split()[1], "type": "managed", "channel": "", "txpower": ""}
                elif line.startswith("type "):
                    cur["type"] = line.split()[1]
                elif line.startswith("channel "):
                    cur["channel"] = line.split()[1]
                elif line.startswith("txpower "):
                    cur["txpower"] = line.split()[1]
            if cur:
                interfaces.append(cur)
                seen.add(cur["name"])
    except Exception:
        pass

    # Method 2: /proc/net/wireless — WEXT drivers (Realtek, Atheros WEXT, etc.)
    try:
        with open("/proc/net/wireless") as f:
            for line in f.readlines()[2:]:  # first two lines are headers
                name = line.split(":")[0].strip()
                if name and name not in seen:
                    interfaces.append({"name": name, "type": "managed", "channel": "", "txpower": ""})
                    seen.add(name)
    except Exception:
        pass

    # Method 3: /sys/class/net sysfs — catch anything still missing
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
        # MAC address
        rc, stdout, _ = run_command(["cat", f"/sys/class/net/{interface}/address"])
        if rc == 0:
            info["mac"] = stdout.strip()

        # Mode: try nl80211 first, then iwconfig for WEXT drivers
        rc, stdout, _ = run_command(["iw", "dev", interface, "info"])
        if rc == 0:
            for line in stdout.split("\n"):
                stripped = line.strip()
                if stripped.startswith("type "):
                    info["mode"] = stripped.split()[1].capitalize()
        else:
            rc2, out2, _ = run_command(["iwconfig", interface])
            if rc2 == 0:
                m = re.search(r"Mode:(\S+)", out2)
                if m:
                    info["mode"] = m.group(1).capitalize()

        # Operstate
        rc, stdout, _ = run_command(["cat", f"/sys/class/net/{interface}/operstate"])
        if rc == 0:
            info["state"] = stdout.strip()
    except Exception:
        pass
    return info


def check_handshake_in_cap(cap_file: str) -> Tuple[bool, str]:
    if not os.path.exists(cap_file):
        return False, "Archivo no encontrado"
    try:
        rc, stdout, _ = run_command(["aircrack-ng", cap_file], timeout=30)
        if "1 handshake" in stdout or rc == 0:
            return True, "Handshake encontrado"
        if "0 handshake" in stdout:
            return False, "No se encontró handshake"
        return False, "No se pudo verificar"
    except Exception as e:
        return False, str(e)


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
                aps.append({
                    "bssid":          parts[0],
                    "first_seen":     parts[1],
                    "last_seen":      parts[2],
                    "channel":        parts[3],
                    "speed":          parts[4],
                    "privacy":        parts[5],
                    "cipher":         parts[6],
                    "authentication": parts[7],
                    "power":          parts[8],
                    "beacons":        parts[9],
                    "iv":             parts[10],
                    "essid":          parts[13] if len(parts) > 13 else "",
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
