#!/usr/bin/env python3
"""
WifiPwn - Escaneo de redes WiFi
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QMessageBox,
    QComboBox, QProgressBar, QCheckBox, QSpinBox, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor

from core.wifi_manager import WiFiManager
from core.config import ConfigManager
from core.database import DatabaseManager
from core.command_runner import CommandRunner


class NetworkScanner(QWidget):
    """Panel de escaneo de redes WiFi"""
    
    log_signal = pyqtSignal(str)
    network_selected = pyqtSignal(dict)  # Emite la red seleccionada
    
    def __init__(self, wifi_manager: WiFiManager, config: ConfigManager,
                 db: DatabaseManager = None, command_runner: CommandRunner = None):
        super().__init__()
        self.wifi_manager = wifi_manager
        self.config = config
        self.db = db
        self.command_runner = command_runner
        self.is_scanning = False
        self.networks = []
        self.selected_network = None
        
        self.init_ui()
        
        # Conectar señal de actualizacion de escaneo
        self.wifi_manager.scan_update.connect(self.on_scan_update)
    
    def init_ui(self):
        """Inicializa la interfaz del panel"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Titulo
        title = QLabel("Escaneo de Redes WiFi")
        title.setFont(QFont("Consolas", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Grupo: Controles de escaneo
        controls_group = QGroupBox("Controles de Escaneo")
        controls_layout = QHBoxLayout(controls_group)
        
        # Seleccion de interfaz
        controls_layout.addWidget(QLabel("Interfaz:"))
        self.iface_combo = QComboBox()
        self.iface_combo.setMinimumWidth(150)
        controls_layout.addWidget(self.iface_combo)
        
        # Filtros
        self.filter_wpa = QCheckBox("Solo WPA/WPA2")
        self.filter_wpa.setChecked(True)
        controls_layout.addWidget(self.filter_wpa)
        
        self.filter_5ghz = QCheckBox("Incluir 5GHz")
        controls_layout.addWidget(self.filter_5ghz)
        
        controls_layout.addStretch()
        
        # Botones
        self.scan_btn = QPushButton("Iniciar Escaneo")
        self.scan_btn.clicked.connect(self.toggle_scan)
        controls_layout.addWidget(self.scan_btn)
        
        self.refresh_btn = QPushButton("Refrescar Interfaces")
        self.refresh_btn.clicked.connect(self.refresh_interfaces)
        controls_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(controls_group)
        
        # Grupo: Resultados del escaneo
        results_group = QGroupBox("Redes Encontradas")
        results_layout = QVBoxLayout(results_group)
        
        # Tabla de redes
        self.networks_table = QTableWidget()
        self.networks_table.setColumnCount(8)
        self.networks_table.setHorizontalHeaderLabels([
            "BSSID", "Canal", "ESSID", "Seguridad", "Senal", "Beacons", "IVs", "Clientes"
        ])
        self.networks_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.networks_table.setSelectionMode(QTableWidget.SingleSelection)
        self.networks_table.itemSelectionChanged.connect(self.on_network_selected)
        self.networks_table.setColumnWidth(0, 140)
        self.networks_table.setColumnWidth(1, 60)
        self.networks_table.setColumnWidth(2, 200)
        self.networks_table.setColumnWidth(3, 100)
        self.networks_table.setColumnWidth(4, 60)
        self.networks_table.setColumnWidth(5, 70)
        self.networks_table.setColumnWidth(6, 60)
        self.networks_table.setColumnWidth(7, 70)
        results_layout.addWidget(self.networks_table)
        
        # Botones de accion
        action_layout = QHBoxLayout()
        
        self.select_btn = QPushButton("Seleccionar como Objetivo")
        self.select_btn.clicked.connect(self.select_target)
        self.select_btn.setEnabled(False)
        action_layout.addWidget(self.select_btn)
        
        self.copy_btn = QPushButton("Copiar BSSID")
        self.copy_btn.clicked.connect(self.copy_bssid)
        self.copy_btn.setEnabled(False)
        action_layout.addWidget(self.copy_btn)
        
        self.export_btn = QPushButton("Exportar Resultados")
        self.export_btn.clicked.connect(self.export_results)
        action_layout.addWidget(self.export_btn)
        
        results_layout.addLayout(action_layout)
        layout.addWidget(results_group)
        
        # Grupo: Informacion de red seleccionada
        info_group = QGroupBox("Informacion de Red Seleccionada")
        info_layout = QVBoxLayout(info_group)
        
        self.network_info = QLabel("Seleccione una red para ver detalles")
        self.network_info.setWordWrap(True)
        self.network_info.setFont(QFont("Consolas", 10))
        info_layout.addWidget(self.network_info)
        
        layout.addWidget(info_group)
        
        # Barra de progreso
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Modo indeterminado
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        layout.addStretch()
        
        # Cargar interfaces
        self.refresh_interfaces()
    
    def refresh_interfaces(self):
        """Refresca la lista de interfaces disponibles"""
        self.iface_combo.clear()
        
        interfaces = self.wifi_manager.get_interfaces()
        for iface in interfaces:
            name = iface.get('name', '')
            mode = iface.get('type', 'unknown')
            self.iface_combo.addItem(f"{name} ({mode})", name)
        
        # Seleccionar interfaz monitor si existe
        if self.wifi_manager.monitor_interface:
            index = self.iface_combo.findData(self.wifi_manager.monitor_interface)
            if index >= 0:
                self.iface_combo.setCurrentIndex(index)
    
    def toggle_scan(self):
        """Inicia o detiene el escaneo"""
        if self.is_scanning:
            self.stop_scan()
        else:
            self.start_scan()
    
    def start_scan(self):
        """Inicia el escaneo de redes"""
        interface = self.iface_combo.currentData()
        
        if not interface:
            QMessageBox.warning(self, "Error", "Seleccione una interfaz")
            return
        
        # Verificar que este en modo monitor
        if not self.wifi_manager.is_monitor_mode(interface):
            reply = QMessageBox.question(
                self,
                "Modo Monitor Requerido",
                f"La interfaz {interface} no esta en modo monitor.\n\n"
                "Desea activarlo ahora?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success, message = self.wifi_manager.enable_monitor_mode(interface)
                if not success:
                    QMessageBox.warning(self, "Error", message)
                    return
                interface = self.wifi_manager.monitor_interface
            else:
                return
        
        self.is_scanning = True
        self.scan_btn.setText("Detener Escaneo")
        self.progress.setVisible(True)
        self.networks = []
        self.networks_table.setRowCount(0)
        
        self.log_signal.emit(f"Iniciando escaneo en {interface}...")
        
        # Iniciar escaneo
        success = self.wifi_manager.start_scan(interface)
        
        if not success:
            self.is_scanning = False
            self.scan_btn.setText("Iniciar Escaneo")
            self.progress.setVisible(False)
            QMessageBox.warning(self, "Error", "No se pudo iniciar el escaneo")
    
    def stop_scan(self):
        """Detiene el escaneo de redes"""
        self.is_scanning = False
        self.wifi_manager.stop_scan()
        self.scan_btn.setText("Iniciar Escaneo")
        self.progress.setVisible(False)
        self.log_signal.emit("Escaneo detenido")
    
    def on_scan_update(self, networks):
        """Maneja la actualizacion de redes del escaneo"""
        self.networks = networks
        self.update_networks_table()
    
    def update_networks_table(self):
        """Actualiza la tabla con las redes encontradas"""
        # Filtrar redes si es necesario
        filtered_networks = self.networks
        
        if self.filter_wpa.isChecked():
            filtered_networks = [
                n for n in filtered_networks 
                if 'WPA' in n.get('privacy', '').upper() or 
                   'WPA2' in n.get('privacy', '').upper() or
                   'WPA3' in n.get('privacy', '').upper()
            ]
        
        self.networks_table.setRowCount(len(filtered_networks))
        
        for i, network in enumerate(filtered_networks):
            bssid = network.get('bssid', '')
            channel = network.get('channel', '')
            essid = network.get('essid', '')
            privacy = network.get('privacy', '')
            power = network.get('power', '')
            beacons = network.get('beacons', '')
            iv = network.get('iv', '')
            
            # Contar clientes asociados (simulado, en implementacion real se contaria)
            clients = "0"
            
            self.networks_table.setItem(i, 0, QTableWidgetItem(bssid))
            self.networks_table.setItem(i, 1, QTableWidgetItem(channel))
            self.networks_table.setItem(i, 2, QTableWidgetItem(essid))
            self.networks_table.setItem(i, 3, QTableWidgetItem(privacy))
            self.networks_table.setItem(i, 4, QTableWidgetItem(power))
            self.networks_table.setItem(i, 5, QTableWidgetItem(beacons))
            self.networks_table.setItem(i, 6, QTableWidgetItem(iv))
            self.networks_table.setItem(i, 7, QTableWidgetItem(clients))
            
            # Colorear segun seguridad
            if 'WEP' in privacy.upper():
                for col in range(8):
                    self.networks_table.item(i, col).setBackground(QColor(255, 200, 200))
            elif 'OPN' in privacy.upper():
                for col in range(8):
                    self.networks_table.item(i, col).setBackground(QColor(255, 255, 200))
    
    def on_network_selected(self):
        """Maneja la seleccion de una red"""
        selected = self.networks_table.selectedItems()
        if selected:
            row = selected[0].row()
            
            # Encontrar la red en la lista
            bssid = self.networks_table.item(row, 0).text()
            for network in self.networks:
                if network.get('bssid') == bssid:
                    self.selected_network = network
                    break
            
            self.select_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)
            
            # Actualizar informacion
            self.update_network_info()
    
    def update_network_info(self):
        """Actualiza la informacion de la red seleccionada"""
        if not self.selected_network:
            return
        
        info_text = f"""
<b>BSSID:</b> {self.selected_network.get('bssid', 'N/A')}<br>
<b>ESSID:</b> {self.selected_network.get('essid', 'N/A')}<br>
<b>Canal:</b> {self.selected_network.get('channel', 'N/A')}<br>
<b>Seguridad:</b> {self.selected_network.get('privacy', 'N/A')}<br>
<b>Cifrado:</b> {self.selected_network.get('cipher', 'N/A')}<br>
<b>Autenticacion:</b> {self.selected_network.get('authentication', 'N/A')}<br>
<b>Potencia:</b> {self.selected_network.get('power', 'N/A')} dBm<br>
<b>Beacons:</b> {self.selected_network.get('beacons', 'N/A')}<br>
        """
        
        self.network_info.setText(info_text)
    
    def select_target(self):
        """Selecciona la red como objetivo"""
        if self.selected_network:
            self.network_selected.emit(self.selected_network)
            self.log_signal.emit(
                f"Red seleccionada: {self.selected_network.get('essid', 'N/A')} "
                f"({self.selected_network.get('bssid', 'N/A')})"
            )
            QMessageBox.information(
                self,
                "Objetivo Seleccionado",
                f"Red seleccionada como objetivo:\n\n"
                f"ESSID: {self.selected_network.get('essid', 'N/A')}\n"
                f"BSSID: {self.selected_network.get('bssid', 'N/A')}\n"
                f"Canal: {self.selected_network.get('channel', 'N/A')}"
            )
    
    def copy_bssid(self):
        """Copia el BSSID al portapapeles"""
        if self.selected_network:
            bssid = self.selected_network.get('bssid', '')
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(bssid)
            self.log_signal.emit(f"BSSID copiado: {bssid}")
    
    def export_results(self):
        """Exporta los resultados del escaneo"""
        from PyQt5.QtWidgets import QFileDialog
        import json
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Resultados",
            str(self.config.get_capture_path("scan_results.json")),
            "JSON Files (*.json);;CSV Files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.networks, f, indent=4)
                self.log_signal.emit(f"Resultados exportados a {filename}")
                QMessageBox.information(self, "Exito", "Resultados exportados correctamente")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudieron exportar los resultados: {e}")
