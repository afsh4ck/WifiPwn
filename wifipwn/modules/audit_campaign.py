#!/usr/bin/env python3
"""
WifiPwn - Campañas de Auditoría
"""

import json
import os
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QMessageBox, QLineEdit, QTextEdit, QTableWidget,
    QTableWidgetItem, QFileDialog, QComboBox, QTabWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from core.config import ConfigManager
from core.database import DatabaseManager


class AuditCampaignPanel(QWidget):
    """Panel de campañas de auditoría"""
    
    log_signal = pyqtSignal(str)
    
    def __init__(self, config: ConfigManager, db: DatabaseManager = None):
        super().__init__()
        self.config = config
        self.db = db
        self.current_campaign = None
        self.campaigns = []
        
        self.init_ui()
        self.load_campaigns_list()
    
    def init_ui(self):
        """Inicializa la interfaz del panel"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Titulo
        title = QLabel("Campañas de Auditoría")
        title.setFont(QFont("Consolas", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Tab: Campaña actual
        current_tab = QWidget()
        current_layout = QVBoxLayout(current_tab)
        
        # Info de campaña
        info_group = QGroupBox("Información de la Campaña")
        info_layout = QVBoxLayout(info_group)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nombre:"))
        self.campaign_name = QLineEdit()
        name_layout.addWidget(self.campaign_name)
        info_layout.addLayout(name_layout)
        
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("Descripción:"))
        self.campaign_desc = QLineEdit()
        desc_layout.addWidget(self.campaign_desc)
        info_layout.addLayout(desc_layout)
        
        current_layout.addWidget(info_group)
        
        # Objetivos
        targets_group = QGroupBox("Objetivos")
        targets_layout = QVBoxLayout(targets_group)
        
        self.targets_table = QTableWidget()
        self.targets_table.setColumnCount(4)
        self.targets_table.setHorizontalHeaderLabels(["BSSID", "ESSID", "Canal", "Estado"])
        targets_layout.addWidget(self.targets_table)
        
        target_btn_layout = QHBoxLayout()
        self.add_target_btn = QPushButton("Agregar Objetivo")
        self.add_target_btn.clicked.connect(self.add_target)
        target_btn_layout.addWidget(self.add_target_btn)
        
        self.remove_target_btn = QPushButton("Eliminar Objetivo")
        self.remove_target_btn.clicked.connect(self.remove_target)
        target_btn_layout.addWidget(self.remove_target_btn)
        
        targets_layout.addLayout(target_btn_layout)
        current_layout.addWidget(targets_group)
        
        # Notas
        notes_group = QGroupBox("Notas y Evidencias")
        notes_layout = QVBoxLayout(notes_group)
        
        self.notes_text = QTextEdit()
        self.notes_text.setPlaceholderText("Notas de la auditoría...")
        notes_layout.addWidget(self.notes_text)
        
        current_layout.addWidget(notes_group)
        
        # Botones de campaña
        campaign_btn_layout = QHBoxLayout()
        
        self.new_campaign_btn = QPushButton("Nueva Campaña")
        self.new_campaign_btn.clicked.connect(self.new_campaign)
        campaign_btn_layout.addWidget(self.new_campaign_btn)
        
        self.save_campaign_btn = QPushButton("Guardar Campaña")
        self.save_campaign_btn.clicked.connect(self.save_campaign)
        campaign_btn_layout.addWidget(self.save_campaign_btn)
        
        self.load_campaign_btn = QPushButton("Cargar Campaña")
        self.load_campaign_btn.clicked.connect(self.load_campaign)
        campaign_btn_layout.addWidget(self.load_campaign_btn)
        
        current_layout.addLayout(campaign_btn_layout)
        
        self.tabs.addTab(current_tab, "Campaña Actual")
        
        # Tab: Reportes
        reports_tab = QWidget()
        reports_layout = QVBoxLayout(reports_tab)
        
        reports_group = QGroupBox("Generación de Reportes")
        reports_group_layout = QVBoxLayout(reports_group)
        
        self.generate_html_btn = QPushButton("Generar Reporte HTML")
        self.generate_html_btn.clicked.connect(lambda: self.generate_report("html"))
        reports_group_layout.addWidget(self.generate_html_btn)
        
        self.generate_pdf_btn = QPushButton("Generar Reporte PDF")
        self.generate_pdf_btn.clicked.connect(lambda: self.generate_report("pdf"))
        reports_group_layout.addWidget(self.generate_pdf_btn)
        
        reports_layout.addWidget(reports_group)
        reports_layout.addStretch()
        
        self.tabs.addTab(reports_tab, "Reportes")
        
        layout.addWidget(self.tabs)
    
    def load_campaigns_list(self):
        """Carga la lista de campañas guardadas"""
        campaigns_dir = Path(self.config.get("capture_directory")).parent / "campaigns"
        if campaigns_dir.exists():
            self.campaigns = list(campaigns_dir.glob("*.json"))
    
    def new_campaign(self):
        """Crea una nueva campaña"""
        self.current_campaign = {
            "name": "",
            "description": "",
            "created": datetime.now().isoformat(),
            "targets": [],
            "notes": "",
            "handshakes": [],
            "results": []
        }
        
        self.campaign_name.clear()
        self.campaign_desc.clear()
        self.targets_table.setRowCount(0)
        self.notes_text.clear()
        
        self.log_signal.emit("Nueva campaña creada")
    
    def save_campaign(self):
        """Guarda la campaña actual"""
        if not self.current_campaign:
            self.current_campaign = {}
        
        self.current_campaign["name"] = self.campaign_name.text()
        self.current_campaign["description"] = self.campaign_desc.text()
        self.current_campaign["notes"] = self.notes_text.toPlainText()
        self.current_campaign["updated"] = datetime.now().isoformat()
        
        # Guardar en archivo
        campaigns_dir = Path(self.config.get("capture_directory")).parent / "campaigns"
        campaigns_dir.mkdir(parents=True, exist_ok=True)
        
        filename = campaigns_dir / f"{self.campaign_name.text() or 'campaign'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.current_campaign, f, indent=4)
            self.log_signal.emit(f"Campaña guardada: {filename}")
            QMessageBox.information(self, "Éxito", "Campaña guardada correctamente")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar: {e}")
    
    def load_campaign(self):
        """Carga una campaña existente"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Cargar Campaña",
            str(Path(self.config.get("capture_directory")).parent / "campaigns"),
            "JSON Files (*.json)"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    self.current_campaign = json.load(f)
                
                self.campaign_name.setText(self.current_campaign.get("name", ""))
                self.campaign_desc.setText(self.current_campaign.get("description", ""))
                self.notes_text.setPlainText(self.current_campaign.get("notes", ""))
                
                # Cargar objetivos
                targets = self.current_campaign.get("targets", [])
                self.targets_table.setRowCount(len(targets))
                for i, target in enumerate(targets):
                    self.targets_table.setItem(i, 0, QTableWidgetItem(target.get("bssid", "")))
                    self.targets_table.setItem(i, 1, QTableWidgetItem(target.get("essid", "")))
                    self.targets_table.setItem(i, 2, QTableWidgetItem(str(target.get("channel", ""))))
                    self.targets_table.setItem(i, 3, QTableWidgetItem(target.get("status", "")))
                
                self.log_signal.emit(f"Campaña cargada: {filename}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo cargar: {e}")
    
    def add_target(self):
        """Agrega un objetivo a la campaña"""
        row = self.targets_table.rowCount()
        self.targets_table.insertRow(row)
        self.targets_table.setItem(row, 0, QTableWidgetItem("00:00:00:00:00:00"))
        self.targets_table.setItem(row, 1, QTableWidgetItem("Nueva Red"))
        self.targets_table.setItem(row, 2, QTableWidgetItem("6"))
        self.targets_table.setItem(row, 3, QTableWidgetItem("Pendiente"))
    
    def remove_target(self):
        """Elimina el objetivo seleccionado"""
        selected = self.targets_table.selectedItems()
        if selected:
            row = selected[0].row()
            self.targets_table.removeRow(row)
    
    def generate_report(self, format_type: str):
        """Genera un reporte de la campaña"""
        if not self.current_campaign:
            QMessageBox.warning(self, "Error", "No hay campaña activa")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == "html":
            self.generate_html_report(timestamp)
        elif format_type == "pdf":
            self.generate_pdf_report(timestamp)
    
    def generate_html_report(self, timestamp: str):
        """Genera reporte HTML"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Reporte HTML",
            str(self.config.get_report_path(f"report_{timestamp}.html")),
            "HTML Files (*.html)"
        )
        
        if filename:
            try:
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Reporte de Auditoría WiFi - {self.current_campaign.get('name', '')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Reporte de Auditoría WiFi</h1>
    <h2>{self.current_campaign.get('name', 'Sin nombre')}</h2>
    <p><strong>Descripción:</strong> {self.current_campaign.get('description', '')}</p>
    <p><strong>Fecha:</strong> {timestamp}</p>
    
    <h2>Objetivos</h2>
    <table>
        <tr>
            <th>BSSID</th>
            <th>ESSID</th>
            <th>Canal</th>
            <th>Estado</th>
        </tr>
"""
                
                for target in self.current_campaign.get('targets', []):
                    html_content += f"""
        <tr>
            <td>{target.get('bssid', '')}</td>
            <td>{target.get('essid', '')}</td>
            <td>{target.get('channel', '')}</td>
            <td>{target.get('status', '')}</td>
        </tr>
"""
                
                html_content += """
    </table>
    
    <h2>Notas</h2>
    <pre>""" + self.current_campaign.get('notes', '') + """</pre>
</body>
</html>
"""
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                self.log_signal.emit(f"Reporte HTML generado: {filename}")
                QMessageBox.information(self, "Éxito", "Reporte generado correctamente")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo generar: {e}")
    
    def generate_pdf_report(self, timestamp: str):
        """Genera reporte PDF"""
        QMessageBox.information(self, "Info", "Generación de PDF requiere implementación adicional")
