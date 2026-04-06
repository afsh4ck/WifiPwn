#!/usr/bin/env python3
"""
WifiPwn - Deauthentication Attack
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QMessageBox, QLineEdit, QSpinBox, QTextEdit,
    QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from core.wifi_manager import WiFiManager
from core.config import ConfigManager
from core.utils import validate_bssid


class DeauthPanel(QWidget):
    """Panel de ataque de deautenticacion"""
    
    log_signal = pyqtSignal(str)
    
    def __init__(self, wifi_manager: WiFiManager, config: ConfigManager):
        super().__init__()
        self.wifi_manager = wifi_manager
        self.config = config
        self.is_attacking = False
        
        self.init_ui()
    
    def init_ui(self):
        """Inicializa la interfaz del panel"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Titulo
        title = QLabel("Ataque de Deautenticacion")
        title.setFont(QFont("Consolas", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Grupo: Configuracion del objetivo
        target_group = QGroupBox("Configuracion del Objetivo")
        target_layout = QVBoxLayout(target_group)
        
        # BSSID del AP
        bssid_layout = QHBoxLayout()
        bssid_layout.addWidget(QLabel("BSSID del AP:"))
        self.bssid_input = QLineEdit()
        self.bssid_input.setPlaceholderText("00:11:22:33:44:55")
        bssid_layout.addWidget(self.bssid_input)
        target_layout.addLayout(bssid_layout)
        
        # Cliente objetivo
        client_layout = QHBoxLayout()
        client_layout.addWidget(QLabel("Cliente (opcional):"))
        self.client_input = QLineEdit()
        self.client_input.setPlaceholderText("Dejar vacio para broadcast")
        client_layout.addWidget(self.client_input)
        target_layout.addLayout(client_layout)
        
        layout.addWidget(target_group)
        
        # Grupo: Opciones de ataque
        options_group = QGroupBox("Opciones de Ataque")
        options_layout = QVBoxLayout(options_group)
        
        # Numero de paquetes
        packets_layout = QHBoxLayout()
        packets_layout.addWidget(QLabel("Numero de paquetes:"))
        self.packets_spin = QSpinBox()
        self.packets_spin.setRange(1, 1000)
        self.packets_spin.setValue(10)
        packets_layout.addWidget(self.packets_spin)
        packets_layout.addStretch()
        options_layout.addLayout(packets_layout)
        
        # Delay entre rafagas
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Delay entre rafagas (ms):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 5000)
        self.delay_spin.setValue(1000)
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addStretch()
        options_layout.addLayout(delay_layout)
        
        # Opciones adicionales
        self.continuous_check = QCheckBox("Ataque continuo")
        options_layout.addWidget(self.continuous_check)
        
        layout.addWidget(options_group)
        
        # Grupo: Estado
        status_group = QGroupBox("Estado del Ataque")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Listo")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Consolas", 12, QFont.Bold))
        status_layout.addWidget(self.status_label)
        
        # Log
        self.attack_log = QTextEdit()
        self.attack_log.setReadOnly(True)
        self.attack_log.setMaximumHeight(200)
        self.attack_log.setFont(QFont("Consolas", 9))
        status_layout.addWidget(self.attack_log)
        
        layout.addWidget(status_group)
        
        # Botones
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Iniciar Ataque")
        self.start_btn.clicked.connect(self.toggle_attack)
        self.start_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.start_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
    
    def toggle_attack(self):
        """Inicia o detiene el ataque"""
        if self.is_attacking:
            self.stop_attack()
        else:
            self.start_attack()
    
    def start_attack(self):
        """Inicia el ataque de deautenticacion"""
        bssid = self.bssid_input.text().strip()
        if not validate_bssid(bssid):
            QMessageBox.warning(self, "Error", "BSSID invalido")
            return
        
        client = self.client_input.text().strip()
        if client and not validate_bssid(client):
            QMessageBox.warning(self, "Error", "MAC del cliente invalida")
            return
        
        packets = self.packets_spin.value()
        
        reply = QMessageBox.question(
            self,
            "Confirmar Ataque",
            f"Enviar {packets} paquetes de deauth a:\n\n"
            f"AP: {bssid}\n"
            f"Cliente: {client if client else 'Broadcast'}\n\n"
            f"Continuar?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.is_attacking = True
            self.start_btn.setText("Detener Ataque")
            self.status_label.setText("ATACANDO...")
            self.status_label.setStyleSheet("color: red;")
            
            success = self.wifi_manager.send_deauth(bssid, client or None, packets)
            
            if success:
                self.log_signal.emit(f"Deauth iniciado contra {bssid}")
                self.attack_log.append(f"Ataque iniciado: {packets} paquetes")
                
                if self.continuous_check.isChecked():
                    self.start_continuous_attack()
            else:
                self.stop_attack()
                QMessageBox.warning(self, "Error", "No se pudo iniciar el ataque")
    
    def start_continuous_attack(self):
        """Inicia ataque continuo con timer"""
        delay = self.delay_spin.value()
        self.attack_timer = QTimer()
        self.attack_timer.timeout.connect(self.send_next_burst)
        self.attack_timer.start(delay)
    
    def send_next_burst(self):
        """Envia la siguiente rafaga de deauth"""
        if not self.is_attacking:
            return
        
        bssid = self.bssid_input.text().strip()
        client = self.client_input.text().strip() or None
        packets = self.packets_spin.value()
        
        self.wifi_manager.send_deauth(bssid, client, packets)
        self.attack_log.append(f"Rafaga enviada: {packets} paquetes")
    
    def stop_attack(self):
        """Detiene el ataque"""
        self.is_attacking = False
        
        if hasattr(self, 'attack_timer'):
            self.attack_timer.stop()
        
        self.wifi_manager.stop_deauth()
        self.start_btn.setText("Iniciar Ataque")
        self.status_label.setText("Detenido")
        self.status_label.setStyleSheet("")
        self.log_signal.emit("Ataque de deauth detenido")
    
    def set_target(self, bssid: str, client: str = None):
        """Establece el objetivo del ataque"""
        self.bssid_input.setText(bssid)
        if client:
            self.client_input.setText(client)
