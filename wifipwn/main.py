#!/usr/bin/env python3
"""
WifiPwn - Herramienta de Pentesting WiFi con GUI
Desarrollada para Kali Linux con PyQt5

Autor: WifiPwn Team
Version: 1.0.0
"""

import sys
import os
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QLabel, QPushButton, QMessageBox,
    QDialog, QTextEdit, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

# Anadir directorio padre al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from core.config import ConfigManager
from core.utils import check_root_privileges, check_required_tools, ToolChecker
from core.wifi_manager import WiFiManager
from core.database import DatabaseManager
from core.command_runner import CommandRunner
from modules.interface_panel import InterfacePanel
from modules.network_scanner import NetworkScanner
from modules.handshake_capture import HandshakeCapture
from modules.cracking import CrackingPanel
from modules.deauth import DeauthPanel
from modules.evil_portal import EvilPortalPanel
from modules.audit_campaign import AuditCampaignPanel
from modules.dashboard import DashboardPanel


class WifiPwnMainWindow(QMainWindow):
    """Ventana principal de la aplicacion WifiPwn"""
    
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.db = DatabaseManager()
        self.command_runner = CommandRunner()
        self.wifi_manager = WiFiManager()
        self.tool_checker = ToolChecker()
        
        self.setWindowTitle("WifiPwn - WiFi Pentesting Tool v2.0")
        self.setGeometry(100, 100, 1600, 1000)
        
        self.init_ui()
        self.apply_theme()
        self.check_prerequisites()
        
        # Conectar señales de la base de datos
        self.db.data_changed.connect(self.on_data_changed)
        
        # Timer para actualizar estado
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)
        
        # Log inicial
        self.log_message("WifiPwn iniciado - Base de datos conectada")
    
    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header con titulo y controles de tema
        header_layout = QHBoxLayout()
        
        title_label = QLabel("WifiPwn - Herramienta de Pentesting WiFi")
        title_label.setFont(QFont("Consolas", 16, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Boton de tema
        self.theme_btn = QPushButton("Modo Oscuro" if self.config.get("theme") == "light" else "Modo Claro")
        self.theme_btn.setFixedWidth(150)
        self.theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_btn)
        
        main_layout.addLayout(header_layout)
        
        # Pestañas principales
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Crear pestañas con acceso a la base de datos
        self.dashboard = DashboardPanel(self.db, self.config)
        self.interface_panel = InterfacePanel(self.wifi_manager, self.config, self.db, self.command_runner)
        self.network_scanner = NetworkScanner(self.wifi_manager, self.config, self.db, self.command_runner)
        self.handshake_capture = HandshakeCapture(self.wifi_manager, self.config, self.db, self.command_runner)
        self.cracking_panel = CrackingPanel(self.config, self.db, self.command_runner)
        self.deauth_panel = DeauthPanel(self.wifi_manager, self.config, self.db, self.command_runner)
        self.evil_portal = EvilPortalPanel(self.wifi_manager, self.config, self.db)
        self.audit_campaign = AuditCampaignPanel(self.config, self.db)
        
        # Añadir pestañas
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.interface_panel, "Interfaces")
        self.tabs.addTab(self.network_scanner, "Escaneo")
        self.tabs.addTab(self.handshake_capture, "Handshake")
        self.tabs.addTab(self.cracking_panel, "Cracking")
        self.tabs.addTab(self.deauth_panel, "Deauth")
        self.tabs.addTab(self.evil_portal, "Evil Portal")
        self.tabs.addTab(self.audit_campaign, "Auditoria")
        
        main_layout.addWidget(self.tabs)
        
        # Consola integrada
        console_label = QLabel("Consola de comandos:")
        console_label.setFont(QFont("Consolas", 10, QFont.Bold))
        main_layout.addWidget(console_label)
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        self.console.setFont(QFont("Consolas", 9))
        main_layout.addWidget(self.console)
        
        # Barra de estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_interface = QLabel("Interfaz: Ninguna")
        self.status_monitor = QLabel("Modo Monitor: Inactivo")
        self.status_action = QLabel("Listo")
        
        self.status_bar.addWidget(self.status_interface)
        self.status_bar.addWidget(self.status_monitor)
        self.status_bar.addPermanentWidget(self.status_action)
        
        # Conectar señales de log
        self.dashboard.log_signal.connect(self.log_message)
        self.interface_panel.log_signal.connect(self.log_message)
        self.network_scanner.log_signal.connect(self.log_message)
        self.handshake_capture.log_signal.connect(self.log_message)
        self.cracking_panel.log_signal.connect(self.log_message)
        self.deauth_panel.log_signal.connect(self.log_message)
        self.evil_portal.log_signal.connect(self.log_message)
        self.audit_campaign.log_signal.connect(self.log_message)
    
    def apply_theme(self):
        """Aplica el tema oscuro o claro"""
        theme = self.config.get("theme", "dark")
        
        if theme == "dark":
            self.setStyleSheet(self.get_dark_stylesheet())
        else:
            self.setStyleSheet(self.get_light_stylesheet())
    
    def get_dark_stylesheet(self):
        """Retorna el stylesheet para tema oscuro"""
        return """
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: 'Consolas', monospace; }
            QTabWidget::pane { border: 1px solid #3c3c3c; background-color: #252526; }
            QTabBar::tab { background-color: #2d2d30; color: #d4d4d4; padding: 10px 20px; border: 1px solid #3c3c3c; border-bottom: none; }
            QTabBar::tab:selected { background-color: #007acc; color: white; }
            QTabBar::tab:hover:!selected { background-color: #3c3c3c; }
            QPushButton { background-color: #0e639c; color: white; border: none; padding: 8px 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #1177bb; }
            QPushButton:pressed { background-color: #094771; }
            QPushButton:disabled { background-color: #3c3c3c; color: #808080; }
            QLineEdit, QComboBox, QTextEdit, QTableWidget { background-color: #3c3c3c; color: #d4d4d4; border: 1px solid #555555; padding: 5px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #3c3c3c; color: #d4d4d4; selection-background-color: #007acc; }
            QTableWidget { gridline-color: #555555; }
            QHeaderView::section { background-color: #2d2d30; color: #d4d4d4; padding: 5px; border: 1px solid #3c3c3c; }
            QProgressBar { border: 1px solid #3c3c3c; background-color: #2d2d30; text-align: center; color: #d4d4d4; }
            QProgressBar::chunk { background-color: #007acc; }
            QStatusBar { background-color: #007acc; color: white; }
            QLabel { color: #d4d4d4; }
            QGroupBox { border: 1px solid #3c3c3c; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QSpinBox, QDoubleSpinBox { background-color: #3c3c3c; color: #d4d4d4; border: 1px solid #555555; }
            QCheckBox { color: #d4d4d4; }
            QRadioButton { color: #d4d4d4; }
            QScrollBar:vertical { background-color: #2d2d30; width: 12px; }
            QScrollBar::handle:vertical { background-color: #3c3c3c; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background-color: #555555; }
        """
    
    def get_light_stylesheet(self):
        """Retorna el stylesheet para tema claro"""
        return """
            QMainWindow { background-color: #f5f5f5; }
            QWidget { background-color: #f5f5f5; color: #333333; font-family: 'Consolas', monospace; }
            QTabWidget::pane { border: 1px solid #cccccc; background-color: #ffffff; }
            QTabBar::tab { background-color: #e0e0e0; color: #333333; padding: 10px 20px; border: 1px solid #cccccc; border-bottom: none; }
            QTabBar::tab:selected { background-color: #0078d4; color: white; }
            QTabBar::tab:hover:!selected { background-color: #d0d0d0; }
            QPushButton { background-color: #0078d4; color: white; border: none; padding: 8px 16px; border-radius: 4px; }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
            QPushButton:disabled { background-color: #cccccc; color: #888888; }
            QLineEdit, QComboBox, QTextEdit, QTableWidget { background-color: #ffffff; color: #333333; border: 1px solid #cccccc; padding: 5px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #ffffff; color: #333333; selection-background-color: #0078d4; }
            QTableWidget { gridline-color: #cccccc; }
            QHeaderView::section { background-color: #e0e0e0; color: #333333; padding: 5px; border: 1px solid #cccccc; }
            QProgressBar { border: 1px solid #cccccc; background-color: #f0f0f0; text-align: center; color: #333333; }
            QProgressBar::chunk { background-color: #0078d4; }
            QStatusBar { background-color: #0078d4; color: white; }
            QLabel { color: #333333; }
            QGroupBox { border: 1px solid #cccccc; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QSpinBox, QDoubleSpinBox { background-color: #ffffff; color: #333333; border: 1px solid #cccccc; }
            QCheckBox { color: #333333; }
            QRadioButton { color: #333333; }
            QScrollBar:vertical { background-color: #f0f0f0; width: 12px; }
            QScrollBar::handle:vertical { background-color: #cccccc; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background-color: #aaaaaa; }
        """
    
    def toggle_theme(self):
        """Alterna entre tema oscuro y claro"""
        current_theme = self.config.get("theme", "dark")
        new_theme = "light" if current_theme == "dark" else "dark"
        self.config.set("theme", new_theme)
        self.config.save()
        
        self.theme_btn.setText("Modo Oscuro" if new_theme == "light" else "Modo Claro")
        self.apply_theme()
        self.log_message(f"Tema cambiado a: {new_theme}")
    
    def check_prerequisites(self):
        """Verifica privilegios de root y herramientas necesarias"""
        # Verificar privilegios de root
        if not check_root_privileges():
            QMessageBox.warning(
                self,
                "Privilegios Insuficientes",
                "Esta aplicacion requiere privilegios de root para funcionar correctamente.\n\n"
                "Por favor, ejecute la aplicacion con:\n"
                "sudo python3 main.py"
            )
        
        # Verificar herramientas requeridas
        missing_tools = self.tool_checker.check_all_tools()
        if missing_tools:
            reply = QMessageBox.question(
                self,
                "Herramientas Faltantes",
                f"Las siguientes herramientas no estan instaladas:\n\n"
                f"{', '.join(missing_tools)}\n\n"
                f"Desea instalarlas ahora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.install_missing_tools(missing_tools)
    
    def install_missing_tools(self, tools):
        """Instala herramientas faltantes"""
        self.log_message(f"Instalando herramientas: {', '.join(tools)}")
        # Implementar instalacion con apt
        for tool in tools:
            try:
                subprocess.run(["apt", "install", "-y", tool], check=True)
                self.log_message(f"{tool} instalado correctamente")
            except subprocess.CalledProcessError as e:
                self.log_message(f"Error instalando {tool}: {e}")
    
    def on_data_changed(self, table_name):
        """Maneja cambios en la base de datos"""
        if table_name == 'all':
            self.log_message("Base de datos limpiada completamente")
        else:
            self.log_message(f"Datos actualizados en tabla: {table_name}")
    
    def update_status(self):
        """Actualiza la barra de estado"""
        interface = self.wifi_manager.get_current_interface()
        if interface:
            self.status_interface.setText(f"Interfaz: {interface}")
            is_monitor = self.wifi_manager.is_monitor_mode(interface)
            self.status_monitor.setText(f"Modo Monitor: {'Activo' if is_monitor else 'Inactivo'}")
        else:
            self.status_interface.setText("Interfaz: Ninguna")
            self.status_monitor.setText("Modo Monitor: Inactivo")
    
    def log_message(self, message):
        """Agrega un mensaje a la consola"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"[{timestamp}] {message}")
        # Auto-scroll al final
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """Maneja el cierre de la aplicacion"""
        reply = QMessageBox.question(
            self,
            "Confirmar Salida",
            "Esta seguro de que desea salir?\n\n"
            "Se detendran todos los procesos activos.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Detener todos los procesos
            self.command_runner.cancel_all()
            self.wifi_manager.cleanup()
            self.db.close()
            event.accept()
        else:
            event.ignore()


def main():
    """Funcion principal de la aplicacion"""
    app = QApplication(sys.argv)
    app.setApplicationName("WifiPwn")
    app.setApplicationVersion("1.0.0")
    
    # Crear y mostrar ventana principal
    window = WifiPwnMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
