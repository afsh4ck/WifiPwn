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
        self._hs_cbs:    List[Callable] = []
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
        for cb in self._hs_cbs:
            try: cb(bssid)
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
            mon = f"{iface}mon"
            for line in stdout.split("\n"):
                if "monitor mode enabled on" in line.lower():
                    m = re.search(r"on \[?([\w\d]+)\]?", line)
                    if m:
                        mon = m.group(1)
                    break
            self.monitor_interface = mon
            self.current_interface = iface
            self._log(f"Modo monitor activo: {mon}")
            return True, f"Modo monitor activado: {mon}"
        err = f"Error: {stderr}"
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
        prefix = str(tmp / "scan")

        try:
            self._scan_process = subprocess.Popen(
                ["airodump-ng", "--write-interval", "1", "--write", prefix,
                 "--output-format", "csv", iface],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            t = threading.Thread(
                target=self._scan_loop,
                args=(prefix + "-01.csv",),
                daemon=True,
            )
            t.start()
            self._log(f"Escaneo iniciado en {iface}")
            return True
        except Exception as e:
            self._scanning = False
            self._log(f"Error iniciando escaneo: {e}")
            return False

    def _scan_loop(self, csv_file: str):
        from core.utils import parse_airodump_csv
        while self._scanning:
            try:
                if os.path.exists(csv_file):
                    aps, _ = parse_airodump_csv(csv_file)
                    self._networks = aps
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
        if on_handshake:
            self._hs_cbs.append(on_handshake)

        try:
            self._capture_process = subprocess.Popen(
                ["airodump-ng", "--channel", str(channel), "--bssid", bssid,
                 "--write", output_prefix, iface],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            threading.Thread(
                target=self._monitor_handshake,
                args=(output_prefix + "-01.cap", bssid),
                daemon=True,
            ).start()
            self._log(f"Captura iniciada: {bssid} canal {channel}")
            return True
        except Exception as e:
            self._capturing = False
            self._log(f"Error captura: {e}")
            return False

    def _monitor_handshake(self, cap_file: str, bssid: str):
        from core.utils import check_handshake_in_cap
        checks = 0
        while self._capturing and checks < 300:
            time.sleep(2)
            checks += 1
            if os.path.exists(cap_file):
                found, _ = check_handshake_in_cap(cap_file)
                if found:
                    self._emit_handshake(bssid)
                    self._log(f"HANDSHAKE detectado: {bssid}")
                    return
        if self._capturing:
            self._log("Timeout: no se capturó handshake")

    def stop_capture(self) -> bool:
        self._capturing = False
        if self._capture_process:
            kill_process(self._capture_process)
            self._capture_process = None
        self._log("Captura detenida")
        return True

    # ------------------------------------------------------------------
    # Deauth
    # ------------------------------------------------------------------

    def send_deauth(self, bssid: str, client: str = None,
                    packets: int = 10, iface: str = None) -> bool:
        iface = iface or self.monitor_interface
        if not iface:
            return False
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
