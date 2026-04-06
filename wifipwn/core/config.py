#!/usr/bin/env python3
"""
WifiPwn - Modulo de configuracion
Gestiona la configuracion de la aplicacion en formato JSON
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Gestor de configuracion de la aplicacion"""
    
    def __init__(self, config_file: Optional[str] = None):
        # Detectar si estamos en Docker
        in_docker = os.path.exists('/.dockerenv')
        
        if in_docker:
            default_capture = "/app/captures"
            default_reports = "/app/reports"
            default_logs = "/app/logs"
        else:
            # En el host, usar directorio del proyecto
            project_dir = Path(__file__).parent.parent.parent
            default_capture = str(project_dir / "captures")
            default_reports = str(project_dir / "reports")
            default_logs = str(project_dir / "logs")
        
        self.DEFAULT_CONFIG = {
            "theme": "dark",
            "language": "es",
            "capture_directory": default_capture,
            "reports_directory": default_reports,
            "logs_directory": default_logs,
            "default_wordlist": "/usr/share/wordlists/rockyou.txt",
            "default_interface": "",
            "auto_save_captures": True,
            "confirm_dangerous_actions": True,
            "scan_timeout": 60,
            "deauth_packets": 10,
            "deauth_delay": 1,
            "evil_portal_templates_dir": "templates",
            "recent_campaigns": [],
            "max_recent_campaigns": 10,
            "window_geometry": {
                "x": 100,
                "y": 100,
                "width": 1400,
                "height": 900
            }
        }
        
        if config_file is None:
            # Directorio de configuracion en home del usuario
            config_dir = Path.home() / ".config" / "wifipwn"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / "config.json"
        else:
            self.config_file = Path(config_file)
        
        self.config = {}
        self.load()
        self.ensure_directories()
    
    def load(self) -> Dict[str, Any]:
        """
        Carga la configuracion desde el archivo JSON
        
        Returns:
            Diccionario con la configuracion cargada
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Fusionar con configuracion por defecto para añadir nuevas claves
                    self.config = {**self.DEFAULT_CONFIG, **loaded_config}
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error cargando configuracion: {e}")
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()
        
        return self.config
    
    def save(self) -> bool:
        """
        Guarda la configuracion actual en el archivo JSON
        
        Returns:
            True si se guardo correctamente, False en caso contrario
        """
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Error guardando configuracion: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuracion
        
        Args:
            key: Clave de configuracion
            default: Valor por defecto si la clave no existe
            
        Returns:
            Valor de configuracion o default
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Establece un valor de configuracion
        
        Args:
            key: Clave de configuracion
            value: Valor a establecer
        """
        self.config[key] = value
    
    def reset(self) -> None:
        """Restaura la configuracion a los valores por defecto"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()
    
    def ensure_directories(self) -> None:
        """Crea los directorios necesarios si no existen"""
        directories = [
            self.get("capture_directory"),
            self.get("reports_directory"),
            self.get("logs_directory"),
        ]
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
    
    def add_recent_campaign(self, campaign_path: str) -> None:
        """
        Añade una campaña a la lista de recientes
        
        Args:
            campaign_path: Ruta a la campaña
        """
        recent = self.get("recent_campaigns", [])
        
        # Eliminar si ya existe para moverla al principio
        if campaign_path in recent:
            recent.remove(campaign_path)
        
        # Añadir al principio
        recent.insert(0, campaign_path)
        
        # Limitar tamaño
        max_recent = self.get("max_recent_campaigns", 10)
        recent = recent[:max_recent]
        
        self.set("recent_campaigns", recent)
        self.save()
    
    def get_window_geometry(self) -> Dict[str, int]:
        """
        Obtiene la geometria de la ventana guardada
        
        Returns:
            Diccionario con x, y, width, height
        """
        return self.get("window_geometry", self.DEFAULT_CONFIG["window_geometry"])
    
    def set_window_geometry(self, x: int, y: int, width: int, height: int) -> None:
        """
        Guarda la geometria de la ventana
        
        Args:
            x: Posicion X
            y: Posicion Y
            width: Ancho
            height: Alto
        """
        self.set("window_geometry", {
            "x": x,
            "y": y,
            "width": width,
            "height": height
        })
        self.save()
    
    def get_capture_path(self, filename: str = "") -> Path:
        """
        Obtiene la ruta completa para un archivo de captura
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Ruta completa
        """
        base_path = Path(self.get("capture_directory"))
        if filename:
            return base_path / filename
        return base_path
    
    def get_report_path(self, filename: str = "") -> Path:
        """
        Obtiene la ruta completa para un archivo de reporte
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Ruta completa
        """
        base_path = Path(self.get("reports_directory"))
        if filename:
            return base_path / filename
        return base_path
    
    def get_log_path(self, filename: str = "") -> Path:
        """
        Obtiene la ruta completa para un archivo de log
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Ruta completa
        """
        base_path = Path(self.get("logs_directory"))
        if filename:
            return base_path / filename
        return base_path
