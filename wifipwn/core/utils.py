#!/usr/bin/env python3
"""
WifiPwn - Utilidades y funciones auxiliares
"""

import re
import os
import subprocess
import shutil
from typing import List, Tuple, Optional, Dict
from pathlib import Path


def check_root_privileges() -> bool:
    """
    Verifica si el script se ejecuta con privilegios de root
    
    Returns:
        True si tiene privilegios de root, False en caso contrario
    """
    return os.geteuid() == 0 if hasattr(os, 'geteuid') else False


def validate_bssid(bssid: str) -> bool:
    """
    Valida el formato de una direccion MAC (BSSID)
    
    Args:
        bssid: Direccion MAC a validar
        
    Returns:
        True si es valida, False en caso contrario
    """
    # Formato: XX:XX:XX:XX:XX:XX o XX-XX-XX-XX-XX-XX
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, bssid))


def normalize_bssid(bssid: str) -> str:
    """
    Normaliza una direccion MAC a formato con dos puntos
    
    Args:
        bssid: Direccion MAC en cualquier formato
        
    Returns:
        Direccion MAC normalizada (XX:XX:XX:XX:XX:XX)
    """
    # Eliminar separadores y convertir a mayusculas
    clean = bssid.replace(':', '').replace('-', '').replace('.', '').upper()
    # Insertar dos puntos cada dos caracteres
    return ':'.join(clean[i:i+2] for i in range(0, 12, 2))


def validate_channel(channel: int) -> bool:
    """
    Valida si un canal WiFi es valido
    
    Args:
        channel: Numero de canal
        
    Returns:
        True si es valido, False en caso contrario
    """
    # Canales 2.4GHz: 1-14
    # Canales 5GHz: 36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 149, 153, 157, 161, 165
    valid_2ghz = list(range(1, 15))
    valid_5ghz = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 149, 153, 157, 161, 165]
    return channel in valid_2ghz or channel in valid_5ghz


def run_command(command: List[str], capture_output: bool = True, 
                timeout: Optional[int] = None, check: bool = False) -> Tuple[int, str, str]:
    """
    Ejecuta un comando del sistema de forma segura
    
    Args:
        command: Lista con el comando y sus argumentos
        capture_output: Si debe capturar stdout/stderr
        timeout: Timeout en segundos
        check: Si debe lanzar excepcion en caso de error
        
    Returns:
        Tupla (codigo_retorno, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            check=check
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def run_command_async(command: List[str], stdout_callback=None, 
                     stderr_callback=None) -> subprocess.Popen:
    """
    Ejecuta un comando de forma asincrona
    
    Args:
        command: Lista con el comando y sus argumentos
        stdout_callback: Funcion callback para stdout
        stderr_callback: Funcion callback para stderr
        
    Returns:
    Objeto Popen del proceso
    """
    return subprocess.Popen(
        command,
        stdout=subprocess.PIPE if stdout_callback else None,
        stderr=subprocess.PIPE if stderr_callback else None,
        text=True,
        bufsize=1,
        universal_newlines=True
    )


def kill_process(process: subprocess.Popen) -> bool:
    """
    Mata un proceso de forma segura
    
    Args:
        process: Objeto Popen del proceso
        
    Returns:
        True si se detuvo correctamente
    """
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        return True
    except Exception as e:
        print(f"Error matando proceso: {e}")
        return False


def get_wireless_interfaces() -> List[Dict[str, str]]:
    """
    Obtiene todas las interfaces inalambricas disponibles
    
    Returns:
        Lista de diccionarios con informacion de cada interfaz
    """
    interfaces = []
    
    try:
        # Usar iw para listar interfaces
        returncode, stdout, stderr = run_command(["iw", "dev"])
        
        if returncode == 0:
            current_iface = {}
            for line in stdout.split('\n'):
                line = line.strip()
                
                if line.startswith('Interface '):
                    if current_iface:
                        interfaces.append(current_iface)
                    current_iface = {
                        'name': line.split()[1],
                        'type': 'managed',
                        'channel': '',
                        'txpower': ''
                    }
                elif line.startswith('type '):
                    current_iface['type'] = line.split()[1]
                elif line.startswith('channel '):
                    parts = line.split()
                    current_iface['channel'] = parts[1]
                    if len(parts) >= 4:
                        current_iface['band'] = parts[3]
                elif line.startswith('txpower '):
                    current_iface['txpower'] = line.split()[1]
            
            if current_iface:
                interfaces.append(current_iface)
    
    except Exception as e:
        print(f"Error obteniendo interfaces: {e}")
    
    # Fallback: usar /sys/class/net
    if not interfaces:
        try:
            for iface in os.listdir('/sys/class/net'):
                if os.path.exists(f'/sys/class/net/{iface}/wireless'):
                    interfaces.append({
                        'name': iface,
                        'type': 'unknown',
                        'channel': '',
                        'txpower': ''
                    })
        except Exception:
            pass
    
    return interfaces


def get_interface_info(interface: str) -> Dict[str, str]:
    """
    Obtiene informacion detallada de una interfaz
    
    Args:
        interface: Nombre de la interfaz
        
    Returns:
        Diccionario con informacion de la interfaz
    """
    info = {
        'name': interface,
        'mac': '',
        'mode': 'unknown',
        'state': 'unknown',
        'chipset': ''
    }
    
    try:
        # Obtener MAC
        returncode, stdout, _ = run_command(["cat", f"/sys/class/net/{interface}/address"])
        if returncode == 0:
            info['mac'] = stdout.strip()
        
        # Obtener modo
        returncode, stdout, _ = run_command(["iw", "dev", interface, "info"])
        if returncode == 0:
            for line in stdout.split('\n'):
                if 'type' in line:
                    info['mode'] = line.split()[-1]
        
        # Obtener estado
        returncode, stdout, _ = run_command(["cat", f"/sys/class/net/{interface}/operstate"])
        if returncode == 0:
            info['state'] = stdout.strip()
    
    except Exception as e:
        print(f"Error obteniendo info de interfaz: {e}")
    
    return info


class ToolChecker:
    """Verifica la disponibilidad de herramientas requeridas"""
    
    REQUIRED_TOOLS = {
        'airmon-ng': 'aircrack-ng',
        'airodump-ng': 'aircrack-ng',
        'aireplay-ng': 'aircrack-ng',
        'aircrack-ng': 'aircrack-ng',
        'hostapd': 'hostapd',
        'dnsmasq': 'dnsmasq',
        'iw': 'iw',
        'iwconfig': 'wireless-tools',
        'macchanger': 'macchanger',
    }
    
    OPTIONAL_TOOLS = {
        'hashcat': 'hashcat',
        'hcxdumptool': 'hcxdumptool',
        'hcxpcapngtool': 'hcxtools',
        'ettercap': 'ettercap-graphical',
        'tshark': 'tshark',
        'reaver': 'reaver',
        'bully': 'bully',
    }
    
    def __init__(self):
        self.missing_required = []
        self.missing_optional = []
    
    def check_tool(self, tool: str) -> bool:
        """
        Verifica si una herramienta esta instalada
        
        Args:
            tool: Nombre de la herramienta
            
        Returns:
            True si esta instalada
        """
        return shutil.which(tool) is not None
    
    def check_all_tools(self) -> List[str]:
        """
        Verifica todas las herramientas requeridas
        
        Returns:
            Lista de herramientas faltantes
        """
        missing = []
        for tool in self.REQUIRED_TOOLS.keys():
            if not self.check_tool(tool):
                missing.append(tool)
        return missing
    
    def check_optional_tools(self) -> List[str]:
        """
        Verifica herramientas opcionales
        
        Returns:
            Lista de herramientas opcionales faltantes
        """
        missing = []
        for tool in self.OPTIONAL_TOOLS.keys():
            if not self.check_tool(tool):
                missing.append(tool)
        return missing
    
    def get_install_command(self, tool: str) -> str:
        """
        Obtiene el comando para instalar una herramienta
        
        Args:
            tool: Nombre de la herramienta
            
        Returns:
            Comando de instalacion
        """
        if tool in self.REQUIRED_TOOLS:
            package = self.REQUIRED_TOOLS[tool]
        elif tool in self.OPTIONAL_TOOLS:
            package = self.OPTIONAL_TOOLS[tool]
        else:
            package = tool
        
        return f"sudo apt install -y {package}"
    
    def install_tool(self, tool: str) -> bool:
        """
        Intenta instalar una herramienta
        
        Args:
            tool: Nombre de la herramienta
            
        Returns:
            True si se instalo correctamente
        """
        package = self.REQUIRED_TOOLS.get(tool) or self.OPTIONAL_TOOLS.get(tool, tool)
        
        try:
            returncode, _, _ = run_command(
                ["apt", "install", "-y", package],
                timeout=300,
                check=True
            )
            return returncode == 0
        except Exception as e:
            print(f"Error instalando {tool}: {e}")
            return False


def check_handshake_in_cap(cap_file: str) -> Tuple[bool, str]:
    """
    Verifica si un archivo .cap contiene un handshake
    
    Args:
        cap_file: Ruta al archivo .cap
        
    Returns:
        Tupla (tiene_handshake, mensaje)
    """
    if not os.path.exists(cap_file):
        return False, "Archivo no encontrado"
    
    try:
        # Usar aircrack-ng para verificar handshake
        returncode, stdout, stderr = run_command(
            ["aircrack-ng", cap_file],
            timeout=30
        )
        
        if returncode == 0 or "1 handshake" in stdout:
            return True, "Handshake encontrado"
        elif "0 handshake" in stdout:
            return False, "No se encontro handshake"
        else:
            return False, "No se pudo verificar el archivo"
    
    except Exception as e:
        return False, f"Error: {e}"


def convert_cap_to_hc22000(cap_file: str, output_file: str) -> bool:
    """
    Convierte un archivo .cap a formato .hc22000 para hashcat
    
    Args:
        cap_file: Ruta al archivo .cap
        output_file: Ruta de salida .hc22000
        
    Returns:
        True si la conversion fue exitosa
    """
    try:
        # Intentar con hcxpcapngtool primero
        returncode, stdout, stderr = run_command(
            ["hcxpcapngtool", "-o", output_file, cap_file],
            timeout=60
        )
        
        if returncode == 0:
            return True
        
        # Fallback: usar aircrack-ng
        returncode, stdout, stderr = run_command(
            ["aircrack-ng", cap_file, "-J", output_file.replace('.hc22000', '')],
            timeout=60
        )
        
        return returncode == 0
    
    except Exception as e:
        print(f"Error convirtiendo archivo: {e}")
        return False


def generate_random_mac() -> str:
    """
    Genera una direccion MAC aleatoria
    
    Returns:
        MAC address en formato XX:XX:XX:XX:XX:XX
    """
    import random
    
    # Generar MAC localmente administrada (bit 1 del primer byte = 1)
    mac = [0x02, random.randint(0x00, 0xff), random.randint(0x00, 0xff),
           random.randint(0x00, 0xff), random.randint(0x00, 0xff), random.randint(0x00, 0xff)]
    
    return ':'.join(f'{b:02x}' for b in mac)


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo eliminando caracteres no seguros
    
    Args:
        filename: Nombre de archivo original
        
    Returns:
        Nombre de archivo seguro
    """
    # Caracteres no permitidos en nombres de archivo
    invalid_chars = '<>:"/\\|?*'
    
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limitar longitud
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename.strip()


def format_bytes(size: int) -> str:
    """
    Formata un tamaño en bytes a formato legible
    
    Args:
        size: Tamaño en bytes
        
    Returns:
        String formateado (ej: "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def parse_airodump_csv(csv_file: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Parsea un archivo CSV generado por airodump-ng
    
    Args:
        csv_file: Ruta al archivo CSV
        
    Returns:
        Tupla (lista_AP, lista_clientes)
    """
    aps = []
    clients = []
    
    try:
        with open(csv_file, 'r') as f:
            lines = f.readlines()
        
        # Separar secciones
        section = 'aps'
        for line in lines:
            line = line.strip()
            
            if not line or line.startswith('BSSID'):
                continue
            
            if 'Station MAC' in line:
                section = 'clients'
                continue
            
            parts = [p.strip() for p in line.split(',')]
            
            if section == 'aps' and len(parts) >= 14:
                aps.append({
                    'bssid': parts[0],
                    'first_seen': parts[1],
                    'last_seen': parts[2],
                    'channel': parts[3],
                    'speed': parts[4],
                    'privacy': parts[5],
                    'cipher': parts[6],
                    'authentication': parts[7],
                    'power': parts[8],
                    'beacons': parts[9],
                    'iv': parts[10],
                    'lan_ip': parts[11],
                    'id_length': parts[12],
                    'essid': parts[13],
                    'key': parts[14] if len(parts) > 14 else ''
                })
            
            elif section == 'clients' and len(parts) >= 6:
                clients.append({
                    'station_mac': parts[0],
                    'first_seen': parts[1],
                    'last_seen': parts[2],
                    'power': parts[3],
                    'packets': parts[4],
                    'bssid': parts[5],
                    'probed_essids': parts[6] if len(parts) > 6 else ''
                })
    
    except Exception as e:
        print(f"Error parseando CSV: {e}")
    
    return aps, clients
