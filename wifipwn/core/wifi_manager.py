#!/usr/bin/env python3
"""
WifiPwn - Gestor de interfaces WiFi
Maneja el modo monitor, escaneo y gestion de interfaces
"""

import os
import re
import subprocess
import threading
from typing import List, Dict, Optional, Callable, Tuple
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from core.utils import run_command, kill_process, get_wireless_interfaces, get_interface_info


class WiFiManager(QObject):
    """Gestiona las interfaces WiFi y operaciones relacionadas"""
    
    # Señales
    scan_update = pyqtSignal(list)  # Lista de redes encontradas
    handshake_detected = pyqtSignal(str)  # BSSID del handshake
    log_message = pyqtSignal(str)  # Mensajes de log
    
    def __init__(self):
        super().__init__()
        self.current_interface = None
        self.monitor_interface = None
        self.scan_process = None
        self.capture_process = None
        self.deauth_process = None
        self._scanning = False
        self._capturing = False
        self._deauthing = False
        self._scan_thread = None
        self._networks = []
    
    def get_interfaces(self) -> List[Dict[str, str]]:
        """
        Obtiene todas las interfaces inalambricas disponibles
        
        Returns:
            Lista de diccionarios con informacion de interfaces
        """
        return get_wireless_interfaces()
    
    def get_interface_details(self, interface: str) -> Dict[str, str]:
        """
        Obtiene detalles de una interfaz especifica
        
        Args:
            interface: Nombre de la interfaz
            
        Returns:
            Diccionario con informacion detallada
        """
        return get_interface_info(interface)
    
    def is_monitor_mode(self, interface: str) -> bool:
        """
        Verifica si una interfaz esta en modo monitor
        
        Args:
            interface: Nombre de la interfaz
            
        Returns:
            True si esta en modo monitor
        """
        info = self.get_interface_details(interface)
        return info.get('mode', '').lower() == 'monitor'
    
    def enable_monitor_mode(self, interface: str) -> Tuple[bool, str]:
        """
        Activa el modo monitor en una interfaz
        
        Args:
            interface: Nombre de la interfaz
            
        Returns:
            Tupla (exito, mensaje)
        """
        self.log_message.emit(f"Activando modo monitor en {interface}...")
        
        # Matar procesos conflictivos
        returncode, stdout, stderr = run_command(["airmon-ng", "check", "kill"])
        if returncode != 0:
            self.log_message.emit(f"Advertencia: No se pudieron matar procesos conflictivos")
        
        # Activar modo monitor
        returncode, stdout, stderr = run_command(["airmon-ng", "start", interface])
        
        if returncode == 0:
            # Buscar el nombre de la interfaz en modo monitor
            lines = stdout.split('\n')
            for line in lines:
                if 'monitor mode enabled on' in line.lower():
                    # Extraer nombre de interfaz monitor
                    match = re.search(r'on \[?([\w\d]+)\]?', line)
                    if match:
                        self.monitor_interface = match.group(1)
                    else:
                        # Formato alternativo: wlan0mon
                        self.monitor_interface = f"{interface}mon"
                    break
            else:
                self.monitor_interface = f"{interface}mon"
            
            self.current_interface = interface
            self.log_message.emit(f"Modo monitor activado en {self.monitor_interface}")
            return True, f"Modo monitor activado: {self.monitor_interface}"
        else:
            error_msg = f"Error activando modo monitor: {stderr}"
            self.log_message.emit(error_msg)
            return False, error_msg
    
    def disable_monitor_mode(self, interface: str = None) -> Tuple[bool, str]:
        """
        Desactiva el modo monitor en una interfaz
        
        Args:
            interface: Nombre de la interfaz (si es None, usa la actual)
            
        Returns:
            Tupla (exito, mensaje)
        """
        if interface is None:
            interface = self.monitor_interface or self.current_interface
        
        if not interface:
            return False, "No hay interfaz seleccionada"
        
        self.log_message.emit(f"Desactivando modo monitor en {interface}...")
        
        returncode, stdout, stderr = run_command(["airmon-ng", "stop", interface])
        
        if returncode == 0:
            self.monitor_interface = None
            self.log_message.emit("Modo monitor desactivado")
            return True, "Modo monitor desactivado"
        else:
            error_msg = f"Error desactivando modo monitor: {stderr}"
            self.log_message.emit(error_msg)
            return False, error_msg
    
    def start_scan(self, interface: str = None, callback: Callable = None) -> bool:
        """
        Inicia un escaneo de redes WiFi
        
        Args:
            interface: Interfaz a usar (si es None, usa la interfaz monitor)
            callback: Funcion callback para actualizaciones
            
        Returns:
            True si se inicio correctamente
        """
        if self._scanning:
            return False
        
        if interface is None:
            interface = self.monitor_interface
        
        if not interface:
            return False
        
        self._scanning = True
        self._networks = []
        
        # Crear directorio temporal para archivos de salida
        temp_dir = Path("/tmp/wifipwn_scan")
        temp_dir.mkdir(exist_ok=True)
        output_prefix = temp_dir / "scan"
        
        # Iniciar airodump-ng
        cmd = [
            "airodump-ng",
            "--write-interval", "1",
            "--write", str(output_prefix),
            "--output-format", "csv",
            interface
        ]
        
        try:
            self.scan_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Iniciar thread para parsear resultados
            self._scan_thread = threading.Thread(
                target=self._parse_scan_results,
                args=(str(output_prefix) + "-01.csv", callback)
            )
            self._scan_thread.daemon = True
            self._scan_thread.start()
            
            self.log_message.emit(f"Escaneo iniciado en {interface}")
            return True
        
        except Exception as e:
            self._scanning = False
            self.log_message.emit(f"Error iniciando escaneo: {e}")
            return False
    
    def _parse_scan_results(self, csv_file: str, callback: Callable = None):
        """
        Parsea los resultados del escaneo en tiempo real
        
        Args:
            csv_file: Ruta al archivo CSV generado por airodump-ng
            callback: Funcion callback para notificar actualizaciones
        """
        import time
        from core.utils import parse_airodump_csv
        
        while self._scanning:
            try:
                if os.path.exists(csv_file):
                    aps, clients = parse_airodump_csv(csv_file)
                    
                    # Actualizar lista de redes
                    self._networks = aps
                    
                    # Emitir señal
                    self.scan_update.emit(aps)
                    
                    # Llamar callback si existe
                    if callback:
                        callback(aps, clients)
                
                time.sleep(2)
            
            except Exception as e:
                self.log_message.emit(f"Error parseando resultados: {e}")
                time.sleep(2)
    
    def stop_scan(self) -> bool:
        """
        Detiene el escaneo de redes
        
        Returns:
            True si se detuvo correctamente
        """
        self._scanning = False
        
        if self.scan_process:
            kill_process(self.scan_process)
            self.scan_process = None
        
        self.log_message.emit("Escaneo detenido")
        return True
    
    def get_networks(self) -> List[Dict[str, str]]:
        """
        Obtiene la lista de redes encontradas en el ultimo escaneo
        
        Returns:
            Lista de diccionarios con informacion de redes
        """
        return self._networks
    
    def start_capture(self, bssid: str, channel: int, output_file: str, 
                      interface: str = None) -> bool:
        """
        Inicia la captura de handshake para una red especifica
        
        Args:
            bssid: MAC address del AP objetivo
            channel: Canal de la red
            output_file: Prefijo del archivo de salida
            interface: Interfaz a usar (si es None, usa la interfaz monitor)
            
        Returns:
            True si se inicio correctamente
        """
        if self._capturing:
            return False
        
        if interface is None:
            interface = self.monitor_interface
        
        if not interface:
            return False
        
        self._capturing = True
        
        # Iniciar airodump-ng para captura especifica
        cmd = [
            "airodump-ng",
            "--channel", str(channel),
            "--bssid", bssid,
            "--write", output_file,
            interface
        ]
        
        try:
            self.capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Iniciar thread para monitorear handshake
            threading.Thread(
                target=self._monitor_handshake,
                args=(output_file + "-01.cap", bssid)
            ).start()
            
            self.log_message.emit(f"Captura iniciada para {bssid} en canal {channel}")
            return True
        
        except Exception as e:
            self._capturing = False
            self.log_message.emit(f"Error iniciando captura: {e}")
            return False
    
    def _monitor_handshake(self, cap_file: str, bssid: str):
        """
        Monitorea un archivo de captura para detectar handshake
        
        Args:
            cap_file: Ruta al archivo .cap
            bssid: BSSID del AP objetivo
        """
        import time
        from core.utils import check_handshake_in_cap
        
        handshake_found = False
        check_count = 0
        
        while self._capturing and not handshake_found and check_count < 300:  # Max 10 minutos
            time.sleep(2)
            check_count += 1
            
            if os.path.exists(cap_file):
                has_handshake, message = check_handshake_in_cap(cap_file)
                if has_handshake:
                    handshake_found = True
                    self.handshake_detected.emit(bssid)
                    self.log_message.emit(f"HANDSHAKE DETECTADO para {bssid}!")
        
        if not handshake_found:
            self.log_message.emit("Tiempo de captura agotado sin handshake")
    
    def stop_capture(self) -> bool:
        """
        Detiene la captura de handshake
        
        Returns:
            True si se detuvo correctamente
        """
        self._capturing = False
        
        if self.capture_process:
            kill_process(self.capture_process)
            self.capture_process = None
        
        self.log_message.emit("Captura detenida")
        return True
    
    def send_deauth(self, bssid: str, client: str = None, 
                    packets: int = 10, interface: str = None) -> bool:
        """
        Envia paquetes de deautenticacion
        
        Args:
            bssid: MAC address del AP
            client: MAC address del cliente (None para broadcast)
            packets: Numero de paquetes a enviar
            interface: Interfaz a usar
            
        Returns:
            True si se envio correctamente
        """
        if interface is None:
            interface = self.monitor_interface
        
        if not interface:
            return False
        
        # Construir comando
        cmd = [
            "aireplay-ng",
            "-0", str(packets),  # Deauth attack
            "-a", bssid          # AP MAC
        ]
        
        if client:
            cmd.extend(["-c", client])  # Client MAC
        
        cmd.append(interface)
        
        try:
            self.deauth_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            client_str = client if client else "broadcast"
            self.log_message.emit(f"Deauth enviado a {client_str} ({packets} paquetes)")
            return True
        
        except Exception as e:
            self.log_message.emit(f"Error enviando deauth: {e}")
            return False
    
    def stop_deauth(self) -> bool:
        """
        Detiene el ataque de deautenticacion
        
        Returns:
            True si se detuvo correctamente
        """
        if self.deauth_process:
            kill_process(self.deauth_process)
            self.deauth_process = None
            self.log_message.emit("Deauth detenido")
        
        return True
    
    def get_current_interface(self) -> Optional[str]:
        """
        Obtiene la interfaz actual seleccionada
        
        Returns:
            Nombre de la interfaz o None
        """
        return self.monitor_interface or self.current_interface
    
    def cleanup(self):
        """Limpia todos los procesos y recursos"""
        self.stop_scan()
        self.stop_capture()
        self.stop_deauth()
        
        # Desactivar modo monitor si esta activo
        if self.monitor_interface:
            self.disable_monitor_mode()
