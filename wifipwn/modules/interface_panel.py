#!/usr/bin/env python3
"""
WifiPwn - Panel de control de interfaces
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QMessageBox,
    QComboBox, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from core.wifi_manager import WiFiManager
from core.config import ConfigManager


class InterfacePanel(QWidget):
    """Panel de control de interfaces WiFi"""
    
    log_signal = pyqtSignal(str)
    
    def __init__(self, wifi_manager: WiFiManager, config: ConfigManager):
        super().__init__()
        self.wifi_manager = wifi_manager
        self.config = config
        self.selected_interface = None
        
        self.init_ui()
        self.refresh_interfaces()
        
        # Timer para actualizar estado
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_interface_status)
        self.update_timer.start(3000)
    
    def init_ui(self):
        """Inicializa la interfaz del panel"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Titulo
        title = QLabel("Panel de Control de Interfaces WiFi")
        title.setFont(QFont("Consolas", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Grupo: Interfaces disponibles
        iface_group = QGroupBox("Interfaces Disponibles")
        iface_layout = QVBoxLayout(iface_group)
        
        # Tabla de interfaces
        self.iface_table = QTableWidget()
        self.iface_table.setColumnCount(5)
        self.iface_table.setHorizontalHeaderLabels([
            "Interfaz", "MAC", "Modo", "Estado", "Chipset"
        ])
        self.iface_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.iface_table.setSelectionMode(QTableWidget.SingleSelection)
        self.iface_table.itemSelectionChanged.connect(self.on_interface_selected)
        self.iface_table.setColumnWidth(0, 120)
        self.iface_table.setColumnWidth(1, 150)
        self.iface_table.setColumnWidth(2, 100)
        self.iface_table.setColumnWidth(3, 100)
        self.iface_table.setColumnWidth(4, 200)
        iface_layout.addWidget(self.iface_table)
        
        # Botones de accion
        btn_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Refrescar")
        self.refresh_btn.clicked.connect(self.refresh_interfaces)
        btn_layout.addWidget(self.refresh_btn)
        
        self.monitor_btn = QPushButton("Activar Modo Monitor")
        self.monitor_btn.clicked.connect(self.toggle_monitor_mode)
        self.monitor_btn.setEnabled(False)
        btn_layout.addWidget(self.monitor_btn)
        
        self.kill_btn = QPushButton("Matar Procesos Conflictivos")
        self.kill_btn.clicked.connect(self.kill_conflicting_processes)
        btn_layout.addWidget(self.kill_btn)
        
        iface_layout.addLayout(btn_layout)
        layout.addWidget(iface_group)
        
        # Grupo: Informacion detallada
        info_group = QGroupBox("Informacion de la Interfaz Seleccionada")
        info_layout = QVBoxLayout(info_group)
        
        self.info_label = QLabel("Seleccione una interfaz para ver detalles")
        self.info_label.setWordWrap(True)
        self.info_label.setFont(QFont("Consolas", 10))
        info_layout.addWidget(self.info_label)
        
        layout.addWidget(info_group)
        
        # Grupo: Acciones rapidas
        actions_group = QGroupBox("Acciones Rapidas")
        actions_layout = QHBoxLayout(actions_group)
        
        self.reset_btn = QPushButton("Resetear Interfaz")
        self.reset_btn.clicked.connect(self.reset_interface)
        self.reset_btn.setEnabled(False)
        actions_layout.addWidget(self.reset_btn)
        
        self.change_mac_btn = QPushButton("Cambiar MAC Aleatoria")
        self.change_mac_btn.clicked.connect(self.change_mac)
        self.change_mac_btn.setEnabled(False)
        actions_layout.addWidget(self.change_mac_btn)
        
        layout.addWidget(actions_group)
        
        layout.addStretch()
    
    def refresh_interfaces(self):
        """Refresca la lista de interfaces disponibles"""
        self.log_signal.emit("Refrescando lista de interfaces...")
        
        interfaces = self.wifi_manager.get_interfaces()
        
        self.iface_table.setRowCount(len(interfaces))
        
        for i, iface in enumerate(interfaces):
            name = iface.get('name', 'Unknown')
            
            # Obtener informacion detallada
            details = self.wifi_manager.get_interface_details(name)
            
            self.iface_table.setItem(i, 0, QTableWidgetItem(name))
            self.iface_table.setItem(i, 1, QTableWidgetItem(details.get('mac', 'N/A')))
            self.iface_table.setItem(i, 2, QTableWidgetItem(details.get('mode', 'N/A')))
            self.iface_table.setItem(i, 3, QTableWidgetItem(details.get('state', 'N/A')))
            self.iface_table.setItem(i, 4, QTableWidgetItem(details.get('chipset', 'N/A')))
        
        self.log_signal.emit(f"{len(interfaces)} interfaces encontradas")
    
    def on_interface_selected(self):
        """Maneja la seleccion de una interfaz en la tabla"""
        selected = self.iface_table.selectedItems()
        if selected:
            row = selected[0].row()
            self.selected_interface = self.iface_table.item(row, 0).text()
            
            # Actualizar botones
            self.monitor_btn.setEnabled(True)
            self.reset_btn.setEnabled(True)
            self.change_mac_btn.setEnabled(True)
            
            # Actualizar informacion
            self.update_interface_info()
    
    def update_interface_info(self):
        """Actualiza la informacion detallada de la interfaz seleccionada"""
        if not self.selected_interface:
            return
        
        details = self.wifi_manager.get_interface_details(self.selected_interface)
        
        info_text = f"""
<b>Interfaz:</b> {details.get('name', 'N/A')}<br>
<b>Direccion MAC:</b> {details.get('mac', 'N/A')}<br>
<b>Modo:</b> {details.get('mode', 'N/A')}<br>
<b>Estado:</b> {details.get('state', 'N/A')}<br>
<b>Chipset:</b> {details.get('chipset', 'N/A')}<br>
        """
        
        self.info_label.setText(info_text)
        
        # Actualizar texto del boton de modo monitor
        is_monitor = details.get('mode', '').lower() == 'monitor'
        self.monitor_btn.setText(
            "Desactivar Modo Monitor" if is_monitor else "Activar Modo Monitor"
        )
    
    def toggle_monitor_mode(self):
        """Activa o desactiva el modo monitor"""
        if not self.selected_interface:
            return
        
        details = self.wifi_manager.get_interface_details(self.selected_interface)
        is_monitor = details.get('mode', '').lower() == 'monitor'
        
        if is_monitor:
            # Desactivar modo monitor
            reply = QMessageBox.question(
                self,
                "Confirmar",
                f"Desea desactivar el modo monitor en {self.selected_interface}?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.log_signal.emit(f"Desactivando modo monitor en {self.selected_interface}...")
                success, message = self.wifi_manager.disable_monitor_mode(self.selected_interface)
                
                if success:
                    QMessageBox.information(self, "Exito", message)
                else:
                    QMessageBox.warning(self, "Error", message)
                
                self.refresh_interfaces()
        else:
            # Activar modo monitor
            reply = QMessageBox.question(
                self,
                "Confirmar",
                f"Desea activar el modo monitor en {self.selected_interface}?\n\n"
                "Esto detendra procesos conflictivos.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.log_signal.emit(f"Activando modo monitor en {self.selected_interface}...")
                success, message = self.wifi_manager.enable_monitor_mode(self.selected_interface)
                
                if success:
                    QMessageBox.information(self, "Exito", message)
                else:
                    QMessageBox.warning(self, "Error", message)
                
                self.refresh_interfaces()
    
    def kill_conflicting_processes(self):
        """Mata procesos conflictivos con airmon-ng"""
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "Esto detendra procesos como NetworkManager, wpa_supplicant, etc.\n\n"
            "Continuar?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.log_signal.emit("Matando procesos conflictivos...")
            
            from core.utils import run_command
            returncode, stdout, stderr = run_command(["airmon-ng", "check", "kill"])
            
            if returncode == 0:
                self.log_signal.emit("Procesos conflictivos detenidos")
                QMessageBox.information(self, "Exito", "Procesos conflictivos detenidos")
            else:
                self.log_signal.emit(f"Error: {stderr}")
                QMessageBox.warning(self, "Error", f"No se pudieron detener todos los procesos:\n{stderr}")
    
    def reset_interface(self):
        """Resetea la interfaz seleccionada"""
        if not self.selected_interface:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"Esto reiniciara la interfaz {self.selected_interface}.\n\n"
            "Continuar?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.log_signal.emit(f"Reseteando interfaz {self.selected_interface}...")
            
            from core.utils import run_command
            
            # Bajar interfaz
            run_command(["ip", "link", "set", self.selected_interface, "down"])
            
            # Subir interfaz
            returncode, stdout, stderr = run_command(["ip", "link", "set", self.selected_interface, "up"])
            
            if returncode == 0:
                self.log_signal.emit("Interfaz reseteada correctamente")
                self.refresh_interfaces()
            else:
                self.log_signal.emit(f"Error reseteando interfaz: {stderr}")
    
    def change_mac(self):
        """Cambia la MAC de la interfaz a una direccion aleatoria"""
        if not self.selected_interface:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"Esto cambiara la MAC de {self.selected_interface} a una direccion aleatoria.\n\n"
            "Continuar?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            from core.utils import run_command, generate_random_mac
            
            new_mac = generate_random_mac()
            self.log_signal.emit(f"Cambiando MAC a {new_mac}...")
            
            # Bajar interfaz
            run_command(["ip", "link", "set", self.selected_interface, "down"])
            
            # Cambiar MAC
            returncode, stdout, stderr = run_command([
                "macchanger", "-m", new_mac, self.selected_interface
            ])
            
            # Subir interfaz
            run_command(["ip", "link", "set", self.selected_interface, "up"])
            
            if returncode == 0:
                self.log_signal.emit(f"MAC cambiada a {new_mac}")
                self.refresh_interfaces()
            else:
                self.log_signal.emit(f"Error cambiando MAC: {stderr}")
    
    def update_interface_status(self):
        """Actualiza el estado de las interfaces periodicamente"""
        if self.selected_interface:
            self.update_interface_info()
