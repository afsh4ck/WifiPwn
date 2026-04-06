#!/usr/bin/env python3
"""
WifiPwn - Captura de Handshake
"""

from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QMessageBox, QLineEdit, QSpinBox, QFileDialog,
    QProgressBar, QTextEdit, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.wifi_manager import WiFiManager
from core.config import ConfigManager
from core.database import DatabaseManager
from core.command_runner import CommandRunner
from core.utils import validate_bssid, validate_channel, check_handshake_in_cap


class HandshakeCapture(QWidget):
    """Panel de captura de handshake WPA/WPA2"""
    
    log_signal = pyqtSignal(str)
    handshake_captured = pyqtSignal(str)
    
    def __init__(self, wifi_manager: WiFiManager, config: ConfigManager,
                 db: DatabaseManager = None, command_runner: CommandRunner = None):
        super().__init__()
        self.wifi_manager = wifi_manager
        self.config = config
        self.db = db
        self.command_runner = command_runner
        self.is_capturing = False
        self.output_file = None
        
        self.init_ui()
        self.wifi_manager.handshake_detected.connect(self.on_handshake_detected)
    
    def init_ui(self):
        """Inicializa la interfaz del panel"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Titulo
        title = QLabel("Captura de Handshake WPA/WPA2")
        title.setFont(QFont("Consolas", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Grupo: Configuracion de objetivo
        target_group = QGroupBox("Configuracion del Objetivo")
        target_layout = QVBoxLayout(target_group)
        
        # BSSID
        bssid_layout = QHBoxLayout()
        bssid_layout.addWidget(QLabel("BSSID (MAC del AP):"))
        self.bssid_input = QLineEdit()
        self.bssid_input.setPlaceholderText("00:11:22:33:44:55")
        bssid_layout.addWidget(self.bssid_input)
        target_layout.addLayout(bssid_layout)
        
        # Canal
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Canal:"))
        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(1, 165)
        self.channel_spin.setValue(6)
        channel_layout.addWidget(self.channel_spin)
        channel_layout.addStretch()
        target_layout.addLayout(channel_layout)
        
        # ESSID
        essid_layout = QHBoxLayout()
        essid_layout.addWidget(QLabel("ESSID (opcional):"))
        self.essid_input = QLineEdit()
        self.essid_input.setPlaceholderText("Nombre de la red")
        essid_layout.addWidget(self.essid_input)
        target_layout.addLayout(essid_layout)
        
        layout.addWidget(target_group)
        
        # Grupo: Configuracion de captura
        capture_group = QGroupBox("Configuracion de Captura")
        capture_layout = QVBoxLayout(capture_group)
        
        # Archivo de salida
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Archivo de salida:"))
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Ruta del archivo .cap")
        output_layout.addWidget(self.output_input)
        
        self.browse_btn = QPushButton("Examinar...")
        self.browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.browse_btn)
        capture_layout.addLayout(output_layout)
        
        # Opciones
        options_layout = QHBoxLayout()
        
        self.auto_deauth = QCheckBox("Enviar Deauth automaticamente")
        self.auto_deauth.setChecked(False)
        options_layout.addWidget(self.auto_deauth)
        
        self.deauth_count = QSpinBox()
        self.deauth_count.setRange(1, 100)
        self.deauth_count.setValue(10)
        options_layout.addWidget(QLabel("Paquetes:"))
        options_layout.addWidget(self.deauth_count)
        
        options_layout.addStretch()
        capture_layout.addLayout(options_layout)
        
        layout.addWidget(capture_group)
        
        # Grupo: Estado de captura
        status_group = QGroupBox("Estado de Captura")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Listo para capturar")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Consolas", 12, QFont.Bold))
        status_layout.addWidget(self.status_label)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        status_layout.addWidget(self.progress)
        
        # Log de captura
        self.capture_log = QTextEdit()
        self.capture_log.setReadOnly(True)
        self.capture_log.setMaximumHeight(150)
        self.capture_log.setFont(QFont("Consolas", 9))
        status_layout.addWidget(self.capture_log)
        
        layout.addWidget(status_group)
        
        # Botones de accion
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Iniciar Captura")
        self.start_btn.clicked.connect(self.toggle_capture)
        self.start_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.start_btn)
        
        self.deauth_btn = QPushButton("Enviar Deauth Manual")
        self.deauth_btn.clicked.connect(self.send_deauth)
        self.deauth_btn.setEnabled(False)
        self.deauth_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.deauth_btn)
        
        self.check_btn = QPushButton("Verificar Handshake")
        self.check_btn.clicked.connect(self.check_handshake)
        self.check_btn.setEnabled(False)
        self.check_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.check_btn)
        
        layout.addLayout(btn_layout)
        
        layout.addStretch()


    def browse_output(self):
        """Abre dialogo para seleccionar archivo de salida"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Captura",
            str(self.config.get_capture_path("handshake")),
            "Capture Files (*.cap);;All Files (*)"
        )
        
        if filename:
            if not filename.endswith(".cap"):
                filename += ".cap"
            self.output_input.setText(filename)
    
    def toggle_capture(self):
        """Inicia o detiene la captura"""
        if self.is_capturing:
            self.stop_capture()
        else:
            self.start_capture()
    
    def start_capture(self):
        """Inicia la captura de handshake"""
        bssid = self.bssid_input.text().strip()
        if not validate_bssid(bssid):
            QMessageBox.warning(self, "Error", "BSSID invalido")
            return
        
        channel = self.channel_spin.value()
        if not validate_channel(channel):
            QMessageBox.warning(self, "Error", "Canal invalido")
            return
        
        output_file = self.output_input.text().strip()
        if not output_file:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            essid = self.essid_input.text().strip() or "unknown"
            output_file = str(self.config.get_capture_path(f"{essid}_{timestamp}"))
            self.output_input.setText(output_file)
        
        interface = self.wifi_manager.get_current_interface()
        if not interface:
            QMessageBox.warning(self, "Error", "No hay interfaz en modo monitor")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmar Captura",
            f"Iniciar captura para:\n\n"
            f"BSSID: {bssid}\n"
            f"Canal: {channel}\n"
            f"Archivo: {output_file}\n\n"
            f"Continuar?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.is_capturing = True
            self.output_file = output_file
            self.start_btn.setText("Detener Captura")
            self.progress.setVisible(True)
            self.status_label.setText("Capturando...")
            self.deauth_btn.setEnabled(True)
            self.check_btn.setEnabled(True)
            
            success = self.wifi_manager.start_capture(bssid, channel, output_file)
            
            if success:
                self.log_signal.emit(f"Captura iniciada para {bssid}")
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.capture_log.append(f"[{timestamp}] Captura iniciada")
                self.capture_log.append(f"BSSID: {bssid}")
                self.capture_log.append(f"Canal: {channel}")
                self.capture_log.append(f"Archivo: {output_file}")
                
                if self.auto_deauth.isChecked():
                    self.send_deauth()
            else:
                self.stop_capture()
                QMessageBox.warning(self, "Error", "No se pudo iniciar la captura")
    
    def stop_capture(self):
        """Detiene la captura de handshake"""
        self.is_capturing = False
        self.wifi_manager.stop_capture()
        self.start_btn.setText("Iniciar Captura")
        self.progress.setVisible(False)
        self.status_label.setText("Captura detenida")
        self.deauth_btn.setEnabled(False)
        self.log_signal.emit("Captura detenida")
    
    def send_deauth(self):
        """Envia paquetes de deautenticacion"""
        bssid = self.bssid_input.text().strip()
        if not validate_bssid(bssid):
            QMessageBox.warning(self, "Error", "BSSID invalido")
            return
        
        packets = self.deauth_count.value()
        
        success = self.wifi_manager.send_deauth(bssid, None, packets)
        
        if success:
            self.log_signal.emit(f"Deauth enviado a {bssid} ({packets} paquetes)")
            self.capture_log.append(f"Deauth enviado: {packets} paquetes")
        else:
            QMessageBox.warning(self, "Error", "No se pudo enviar el deauth")
    
    def check_handshake(self):
        """Verifica si se ha capturado un handshake"""
        if not self.output_file:
            QMessageBox.warning(self, "Error", "No hay archivo de captura")
            return
        
        cap_file = self.output_file + "-01.cap"
        
        has_handshake, message = check_handshake_in_cap(cap_file)
        
        if has_handshake:
            self.status_label.setText("HANDSHAKE CAPTURADO!")
            self.status_label.setStyleSheet("color: green;")
            QMessageBox.information(self, "Exito", "Handshake capturado correctamente!")
        else:
            self.status_label.setText("Handshake no encontrado")
            QMessageBox.information(self, "Estado", message)
        
        self.capture_log.append(f"Verificacion: {message}")
    
    def on_handshake_detected(self, bssid):
        """Maneja la deteccion de handshake"""
        self.status_label.setText("HANDSHAKE DETECTADO!")
        self.status_label.setStyleSheet("color: green;")
        self.capture_log.append("HANDSHAKE DETECTADO!")
        self.handshake_captured.emit(self.output_file)
        
        if self.config.get("auto_save_captures", True):
            self.log_signal.emit(f"Handshake guardado en: {self.output_file}")

