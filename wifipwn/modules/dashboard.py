#!/usr/bin/env python3
"""
WifiPwn - Dashboard Principal
Muestra estadisticas y permite gestionar datos
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QGridLayout, QFrame, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor

from core.database import DatabaseManager
from core.config import ConfigManager


class StatCard(QFrame):
    """Tarjeta de estadistica"""
    
    def __init__(self, title: str, value: str = "0", color: str = "#007acc"):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet(f"""
            StatCard {{
                background-color: #2d2d30;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Consolas", 10))
        self.title_label.setStyleSheet("color: #888;")
        layout.addWidget(self.title_label)
        
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Consolas", 24, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
    
    def set_value(self, value: str):
        self.value_label.setText(value)


class DashboardPanel(QWidget):
    """Panel principal del dashboard"""
    
    log_signal = pyqtSignal(str)
    
    def __init__(self, db: DatabaseManager, config: ConfigManager):
        super().__init__()
        self.db = db
        self.config = config
        
        self.init_ui()
        self.refresh_stats()
        
        # Timer para actualizar estadisticas
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.refresh_stats)
        self.stats_timer.start(5000)  # Actualizar cada 5 segundos
    
    def init_ui(self):
        """Inicializa la interfaz"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Titulo
        title = QLabel("Dashboard - Vista General")
        title.setFont(QFont("Consolas", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Tarjetas de estadisticas
        stats_group = QGroupBox("Estadisticas")
        stats_layout = QGridLayout(stats_group)
        
        self.card_networks = StatCard("Redes Descubiertas", "0", "#4CAF50")
        self.card_handshakes = StatCard("Handshakes Capturados", "0", "#FF9800")
        self.card_cracked = StatCard("Handshakes Crackeados", "0", "#F44336")
        self.card_credentials = StatCard("Credenciales Capturadas", "0", "#9C27B0")
        self.card_campaigns = StatCard("Campañas Activas", "0", "#2196F3")
        self.card_deauth = StatCard("Ataques Deauth", "0", "#FF5722")
        
        stats_layout.addWidget(self.card_networks, 0, 0)
        stats_layout.addWidget(self.card_handshakes, 0, 1)
        stats_layout.addWidget(self.card_cracked, 0, 2)
        stats_layout.addWidget(self.card_credentials, 1, 0)
        stats_layout.addWidget(self.card_campaigns, 1, 1)
        stats_layout.addWidget(self.card_deauth, 1, 2)
        
        layout.addWidget(stats_group)
        
        # Panel de gestion de datos
        data_group = QGroupBox("Gestion de Datos")
        data_layout = QHBoxLayout(data_group)
        
        # Botones de limpieza
        self.clear_networks_btn = QPushButton("Limpiar Redes")
        self.clear_networks_btn.clicked.connect(lambda: self.clear_data("networks"))
        data_layout.addWidget(self.clear_networks_btn)
        
        self.clear_handshakes_btn = QPushButton("Limpiar Handshakes")
        self.clear_handshakes_btn.clicked.connect(lambda: self.clear_data("handshakes"))
        data_layout.addWidget(self.clear_handshakes_btn)
        
        self.clear_credentials_btn = QPushButton("Limpiar Credenciales")
        self.clear_credentials_btn.clicked.connect(lambda: self.clear_data("credentials"))
        data_layout.addWidget(self.clear_credentials_btn)
        
        self.clear_all_btn = QPushButton("LIMPIAR TODO")
        self.clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        self.clear_all_btn.clicked.connect(self.clear_all_data)
        data_layout.addWidget(self.clear_all_btn)
        
        layout.addWidget(data_group)
        
        # Ultimas actividades
        activity_group = QGroupBox("Ultimas Actividades")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels(["Fecha", "Accion", "Detalles", "Estado"])
        self.activity_table.setColumnWidth(0, 150)
        self.activity_table.setColumnWidth(1, 200)
        self.activity_table.setColumnWidth(2, 400)
        self.activity_table.setColumnWidth(3, 100)
        activity_layout.addWidget(self.activity_table)
        
        layout.addWidget(activity_group)
        
        # Boton de exportacion
        export_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("Exportar Datos a JSON")
        self.export_btn.clicked.connect(self.export_data)
        export_layout.addWidget(self.export_btn)
        
        self.refresh_btn = QPushButton("Actualizar Estadisticas")
        self.refresh_btn.clicked.connect(self.refresh_stats)
        export_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(export_layout)
        layout.addStretch()
    
    def refresh_stats(self):
        """Actualiza las estadisticas"""
        stats = self.db.get_statistics()
        
        self.card_networks.set_value(str(stats.get('total_networks', 0)))
        self.card_handshakes.set_value(str(stats.get('total_handshakes', 0)))
        self.card_cracked.set_value(str(stats.get('cracked_handshakes', 0)))
        self.card_credentials.set_value(str(stats.get('total_credentials', 0)))
        self.card_campaigns.set_value(str(stats.get('total_campaigns', 0)))
        self.card_deauth.set_value(str(stats.get('total_deauth_attacks', 0)))
        
        # Actualizar actividades recientes
        self.refresh_activity()
    
    def refresh_activity(self):
        """Actualiza la tabla de actividades"""
        logs = self.db.get_recent_logs(limit=20)
        
        self.activity_table.setRowCount(len(logs))
        for i, log in enumerate(logs):
            self.activity_table.setItem(i, 0, QTableWidgetItem(str(log.get('timestamp', ''))))
            self.activity_table.setItem(i, 1, QTableWidgetItem(str(log.get('action', ''))))
            self.activity_table.setItem(i, 2, QTableWidgetItem(str(log.get('details', ''))))
            
            status = "OK" if log.get('success', 1) else "ERROR"
            status_item = QTableWidgetItem(status)
            if not log.get('success', 1):
                status_item.setBackground(QColor("#F44336"))
                status_item.setForeground(QColor("white"))
            self.activity_table.setItem(i, 3, status_item)
    
    def clear_data(self, table_name: str):
        """Limpia una tabla especifica"""
        reply = QMessageBox.question(
            self,
            "Confirmar Limpieza",
            f"Esta seguro de que desea limpiar todos los datos de {table_name}?\n\n"
            "Esta accion no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.clear_table(table_name):
                self.log_signal.emit(f"Datos de {table_name} limpiados")
                self.refresh_stats()
                QMessageBox.information(self, "Exito", f"Datos de {table_name} limpiados correctamente")
            else:
                QMessageBox.warning(self, "Error", f"No se pudieron limpiar los datos de {table_name}")
    
    def clear_all_data(self):
        """Limpia toda la base de datos"""
        reply = QMessageBox.warning(
            self,
            "ATENCION - Limpieza Total",
            "Esta a punto de ELIMINAR TODOS LOS DATOS de la base de datos.\n\n"
            "Incluye:\n"
            "- Todas las redes descubiertas\n"
            "- Todos los handshakes capturados\n"
            "- Todas las credenciales\n"
            "- Todas las campañas\n\n"
            "Esta accion NO SE PUEDE DESHACER.\n\n"
            "¿Esta completamente seguro?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Segunda confirmacion
            reply2 = QMessageBox.critical(
                self,
                "CONFIRMACION FINAL",
                "ESTA ES UNA ACCION DESTRUCTIVA.\n\n"
                "Escriba 'ELIMINAR' en el siguiente cuadro para confirmar:",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply2 == QMessageBox.Yes:
                if self.db.clear_all_data():
                    self.log_signal.emit("TODOS LOS DATOS HAN SIDO ELIMINADOS")
                    self.refresh_stats()
                    QMessageBox.information(self, "Completado", "Base de datos limpiada completamente")
                else:
                    QMessageBox.critical(self, "Error", "Error al limpiar la base de datos")
    
    def export_data(self):
        """Exporta todos los datos a JSON"""
        from PyQt5.QtWidgets import QFileDialog
        from datetime import datetime
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Datos",
            f"wifipwn_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if filename:
            try:
                self.db.export_to_json(filename)
                self.log_signal.emit(f"Datos exportados a: {filename}")
                QMessageBox.information(self, "Exito", "Datos exportados correctamente")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error al exportar: {e}")
