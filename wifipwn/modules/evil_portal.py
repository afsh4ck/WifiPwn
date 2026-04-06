#!/usr/bin/env python3
"""
WifiPwn - Evil Portal (Punto de Acceso Falso)
"""

import os
import subprocess
import threading
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QMessageBox, QLineEdit, QSpinBox, QTextEdit,
    QComboBox, QFileDialog, QCheckBox, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from core.wifi_manager import WiFiManager
from core.config import ConfigManager


class EvilPortalPanel(QWidget):
    """Panel de Evil Portal - Punto de acceso falso"""
    
    log_signal = pyqtSignal(str)
    credential_captured = pyqtSignal(str, str)  # usuario, password
    
    def __init__(self, wifi_manager: WiFiManager, config: ConfigManager):
        super().__init__()
        self.wifi_manager = wifi_manager
        self.config = config
        self.is_running = False
        self.hostapd_process = None
        self.dnsmasq_process = None
        self.credentials = []
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializa la interfaz del panel"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Titulo
        title = QLabel("Evil Portal - Punto de Acceso Falso")
        title.setFont(QFont("Consolas", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Grupo: Configuracion del AP
        ap_group = QGroupBox("Configuracion del Access Point")
        ap_layout = QVBoxLayout(ap_group)
        
        # ESSID
        essid_layout = QHBoxLayout()
        essid_layout.addWidget(QLabel("ESSID:"))
        self.essid_input = QLineEdit()
        self.essid_input.setText("FreeWiFi")
        essid_layout.addWidget(self.essid_input)
        ap_layout.addLayout(essid_layout)
        
        # Canal
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Canal:"))
        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(1, 14)
        self.channel_spin.setValue(6)
        channel_layout.addWidget(self.channel_spin)
        channel_layout.addStretch()
        ap_layout.addLayout(channel_layout)
        
        # Password (opcional)
        pass_layout = QHBoxLayout()
        pass_layout.addWidget(QLabel("Password (opcional):"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Dejar vacio para AP abierto")
        pass_layout.addWidget(self.password_input)
        ap_layout.addLayout(pass_layout)
        
        # Interfaz
        iface_layout = QHBoxLayout()
        iface_layout.addWidget(QLabel("Interfaz:"))
        self.iface_combo = QComboBox()
        iface_layout.addWidget(self.iface_combo)
        iface_layout.addStretch()
        ap_layout.addLayout(iface_layout)
        
        layout.addWidget(ap_group)
        
        # Grupo: Plantilla
        template_group = QGroupBox("Plantilla del Portal")
        template_layout = QVBoxLayout(template_group)
        
        template_file_layout = QHBoxLayout()
        template_file_layout.addWidget(QLabel("Plantilla HTML:"))
        self.template_input = QLineEdit()
        self.template_input.setText("templates/default_portal.html")
        template_file_layout.addWidget(self.template_input)
        
        self.template_browse_btn = QPushButton("Examinar...")
        self.template_browse_btn.clicked.connect(self.browse_template)
        template_file_layout.addWidget(self.template_browse_btn)
        template_layout.addLayout(template_file_layout)
        
        layout.addWidget(template_group)
        
        # Grupo: Credenciales capturadas
        creds_group = QGroupBox("Credenciales Capturadas")
        creds_layout = QVBoxLayout(creds_group)
        
        self.creds_table = QTableWidget()
        self.creds_table.setColumnCount(3)
        self.creds_table.setHorizontalHeaderLabels(["Hora", "Usuario", "Password"])
        self.creds_table.setColumnWidth(0, 100)
        self.creds_table.setColumnWidth(1, 150)
        self.creds_table.setColumnWidth(2, 150)
        creds_layout.addWidget(self.creds_table)
        
        creds_btn_layout = QHBoxLayout()
        
        self.clear_creds_btn = QPushButton("Limpiar")
        self.clear_creds_btn.clicked.connect(self.clear_credentials)
        creds_btn_layout.addWidget(self.clear_creds_btn)
        
        self.save_creds_btn = QPushButton("Guardar")
        self.save_creds_btn.clicked.connect(self.save_credentials)
        creds_btn_layout.addWidget(self.save_creds_btn)
        
        creds_layout.addLayout(creds_btn_layout)
        layout.addWidget(creds_group)
        
        # Grupo: Log
        log_group = QGroupBox("Log del Portal")
        log_layout = QVBoxLayout(log_group)
        
        self.portal_log = QTextEdit()
        self.portal_log.setReadOnly(True)
        self.portal_log.setMaximumHeight(150)
        self.portal_log.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.portal_log)
        
        layout.addWidget(log_group)
        
        # Botones de control
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Iniciar Evil Portal")
        self.start_btn.clicked.connect(self.toggle_portal)
        self.start_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.start_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        # Refrescar interfaces
        self.refresh_interfaces()
    
    def refresh_interfaces(self):
        """Refresca la lista de interfaces"""
        self.iface_combo.clear()
        interfaces = self.wifi_manager.get_interfaces()
        for iface in interfaces:
            self.iface_combo.addItem(iface.get('name', ''), iface.get('name'))
    
    def browse_template(self):
        """Abre dialogo para seleccionar plantilla"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Plantilla",
            "templates",
            "HTML Files (*.html);;All Files (*)"
        )
        if filename:
            self.template_input.setText(filename)
    
    def toggle_portal(self):
        """Inicia o detiene el evil portal"""
        if self.is_running:
            self.stop_portal()
        else:
            self.start_portal()
    
    def start_portal(self):
        """Inicia el evil portal"""
        essid = self.essid_input.text().strip()
        if not essid:
            QMessageBox.warning(self, "Error", "Ingrese un ESSID")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"Iniciar Evil Portal con ESSID: {essid}?\n\n"
            "Esto creara un punto de acceso falso.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.is_running = True
            self.start_btn.setText("Detener Evil Portal")
            self.portal_log.append(f"Iniciando Evil Portal: {essid}")
            self.log_signal.emit(f"Evil Portal iniciado: {essid}")
            
            # Simular captura de credenciales (en implementacion real usaria hostapd + dnsmasq)
            self.start_credential_monitor()
    
    def start_credential_monitor(self):
        """Inicia monitoreo de credenciales"""
        # En implementacion real, esto monitorearia logs de dnsmasq/hostapd
        pass
    
    def add_credential(self, username: str, password: str):
        """Agrega una credencial capturada"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.credentials.append((timestamp, username, password))
        
        row = self.creds_table.rowCount()
        self.creds_table.insertRow(row)
        self.creds_table.setItem(row, 0, QTableWidgetItem(timestamp))
        self.creds_table.setItem(row, 1, QTableWidgetItem(username))
        self.creds_table.setItem(row, 2, QTableWidgetItem(password))
        
        self.credential_captured.emit(username, password)
        self.portal_log.append(f"Credencial capturada: {username}")
        self.log_signal.emit(f"Credencial capturada en Evil Portal")
    
    def clear_credentials(self):
        """Limpia la tabla de credenciales"""
        self.credentials.clear()
        self.creds_table.setRowCount(0)
    
    def save_credentials(self):
        """Guarda las credenciales en archivo"""
        from PyQt5.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Credenciales",
            str(self.config.get_report_path("credentials.txt")),
            "Text Files (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    for ts, user, pwd in self.credentials:
                        f.write(f"[{ts}] {user}:{pwd}\n")
                self.log_signal.emit(f"Credenciales guardadas en {filename}")
                QMessageBox.information(self, "Exito", "Credenciales guardadas")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudieron guardar: {e}")
    
    def stop_portal(self):
        """Detiene el evil portal"""
        self.is_running = False
        
        if self.hostapd_process:
            self.hostapd_process.terminate()
            self.hostapd_process = None
        
        if self.dnsmasq_process:
            self.dnsmasq_process.terminate()
            self.dnsmasq_process = None
        
        self.start_btn.setText("Iniciar Evil Portal")
        self.portal_log.append("Evil Portal detenido")
        self.log_signal.emit("Evil Portal detenido")
