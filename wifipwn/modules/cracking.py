#!/usr/bin/env python3
"""
WifiPwn - Modulo de Cracking de Handshakes
"""

import os
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QMessageBox, QLineEdit, QFileDialog, QTextEdit,
    QProgressBar, QComboBox, QTableWidget, QTableWidgetItem,
    QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor

from core.config import ConfigManager
from core.database import DatabaseManager
from core.command_runner import CommandRunner


class CrackingPanel(QWidget):
    """Panel de cracking de handshakes WPA/WPA2"""

    log_signal = pyqtSignal(str)

    def __init__(self, config: ConfigManager, db: DatabaseManager = None,
                 command_runner: CommandRunner = None):
        super().__init__()
        self.config = config
        self.db = db
        self.command_runner = command_runner
        self.is_cracking = False
        self.current_cmd_id = None

        self.init_ui()
        self.refresh_handshakes()

        if self.command_runner:
            self.command_runner.command_finished.connect(self.on_command_finished)
            self.command_runner.command_progress.connect(self.on_command_progress)

    def init_ui(self):
        """Inicializa la interfaz del panel"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Titulo
        title = QLabel("Cracking de Handshakes WPA/WPA2")
        title.setFont(QFont("Consolas", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Grupo: Seleccion de handshake
        hs_group = QGroupBox("Handshake a Crackear")
        hs_layout = QVBoxLayout(hs_group)

        # Archivo .cap
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Archivo .cap:"))
        self.cap_input = QLineEdit()
        self.cap_input.setPlaceholderText("Ruta al archivo de captura")
        file_layout.addWidget(self.cap_input)

        self.browse_btn = QPushButton("Examinar...")
        self.browse_btn.clicked.connect(self.browse_cap)
        file_layout.addWidget(self.browse_btn)
        hs_layout.addLayout(file_layout)

        # BSSID
        bssid_layout = QHBoxLayout()
        bssid_layout.addWidget(QLabel("BSSID (opcional):"))
        self.bssid_input = QLineEdit()
        self.bssid_input.setPlaceholderText("00:11:22:33:44:55")
        bssid_layout.addWidget(self.bssid_input)
        hs_layout.addLayout(bssid_layout)

        layout.addWidget(hs_group)

        # Grupo: Metodo de cracking
        method_group = QGroupBox("Metodo de Cracking")
        method_layout = QVBoxLayout(method_group)

        # Herramienta
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(QLabel("Herramienta:"))
        self.tool_combo = QComboBox()
        self.tool_combo.addItem("aircrack-ng", "aircrack-ng")
        self.tool_combo.addItem("hashcat", "hashcat")
        tool_layout.addWidget(self.tool_combo)
        tool_layout.addStretch()
        method_layout.addLayout(tool_layout)

        # Wordlist
        wl_layout = QHBoxLayout()
        wl_layout.addWidget(QLabel("Wordlist:"))
        self.wordlist_input = QLineEdit()
        self.wordlist_input.setText(self.config.get("default_wordlist", "/usr/share/wordlists/rockyou.txt"))
        wl_layout.addWidget(self.wordlist_input)

        self.wl_browse_btn = QPushButton("Examinar...")
        self.wl_browse_btn.clicked.connect(self.browse_wordlist)
        wl_layout.addWidget(self.wl_browse_btn)
        method_layout.addLayout(wl_layout)

        layout.addWidget(method_group)

        # Grupo: Progreso
        progress_group = QGroupBox("Progreso")
        progress_layout = QVBoxLayout(progress_group)

        self.status_label = QLabel("Listo")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Consolas", 12, QFont.Bold))
        progress_layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        progress_layout.addWidget(self.progress)

        # Log de cracking
        self.crack_log = QTextEdit()
        self.crack_log.setReadOnly(True)
        self.crack_log.setMaximumHeight(200)
        self.crack_log.setFont(QFont("Consolas", 9))
        progress_layout.addWidget(self.crack_log)

        layout.addWidget(progress_group)

        # Grupo: Handshakes de la BD
        db_group = QGroupBox("Handshakes en Base de Datos")
        db_layout = QVBoxLayout(db_group)

        self.hs_table = QTableWidget()
        self.hs_table.setColumnCount(5)
        self.hs_table.setHorizontalHeaderLabels([
            "Red (ESSID)", "BSSID", "Archivo", "Crackeado", "Password"
        ])
        self.hs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.hs_table.setSelectionMode(QTableWidget.SingleSelection)
        self.hs_table.itemSelectionChanged.connect(self.on_hs_selected)
        self.hs_table.setColumnWidth(0, 150)
        self.hs_table.setColumnWidth(1, 140)
        self.hs_table.setColumnWidth(2, 250)
        self.hs_table.setColumnWidth(3, 80)
        self.hs_table.setColumnWidth(4, 150)
        db_layout.addWidget(self.hs_table)

        refresh_layout = QHBoxLayout()
        self.refresh_hs_btn = QPushButton("Refrescar")
        self.refresh_hs_btn.clicked.connect(self.refresh_handshakes)
        refresh_layout.addWidget(self.refresh_hs_btn)
        refresh_layout.addStretch()
        db_layout.addLayout(refresh_layout)

        layout.addWidget(db_group)

        # Botones de accion
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("Iniciar Cracking")
        self.start_btn.clicked.connect(self.toggle_cracking)
        self.start_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Detener")
        self.stop_btn.clicked.connect(self.stop_cracking)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

    def browse_cap(self):
        """Abre dialogo para seleccionar archivo .cap"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Captura",
            str(self.config.get_capture_path()),
            "Capture Files (*.cap *.pcap *.hc22000);;All Files (*)"
        )
        if filename:
            self.cap_input.setText(filename)

    def browse_wordlist(self):
        """Abre dialogo para seleccionar wordlist"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Wordlist",
            "/usr/share/wordlists/",
            "Text Files (*.txt *.lst);;All Files (*)"
        )
        if filename:
            self.wordlist_input.setText(filename)

    def refresh_handshakes(self):
        """Refresca la tabla de handshakes desde la BD"""
        if not self.db:
            return

        try:
            networks = self.db.get_all_networks()
            rows = []
            for net in networks:
                handshakes = self.db.get_handshakes_by_network(net['id'])
                for hs in handshakes:
                    rows.append({
                        'essid': net.get('essid', ''),
                        'bssid': net.get('bssid', ''),
                        'file': hs.get('capture_file', ''),
                        'cracked': hs.get('cracked', 0),
                        'password': hs.get('password', '') or ''
                    })

            self.hs_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.hs_table.setItem(i, 0, QTableWidgetItem(row['essid']))
                self.hs_table.setItem(i, 1, QTableWidgetItem(row['bssid']))
                self.hs_table.setItem(i, 2, QTableWidgetItem(row['file']))

                cracked_text = "Si" if row['cracked'] else "No"
                cracked_item = QTableWidgetItem(cracked_text)
                if row['cracked']:
                    cracked_item.setBackground(QColor("#4CAF50"))
                    cracked_item.setForeground(QColor("white"))
                self.hs_table.setItem(i, 3, cracked_item)
                self.hs_table.setItem(i, 4, QTableWidgetItem(row['password']))
        except Exception as e:
            self.log_signal.emit(f"Error cargando handshakes: {e}")

    def on_hs_selected(self):
        """Maneja la seleccion de un handshake en la tabla"""
        selected = self.hs_table.selectedItems()
        if selected:
            row = selected[0].row()
            cap_file = self.hs_table.item(row, 2).text()
            bssid = self.hs_table.item(row, 1).text()
            self.cap_input.setText(cap_file)
            self.bssid_input.setText(bssid)

    def toggle_cracking(self):
        """Inicia o detiene el cracking"""
        if self.is_cracking:
            self.stop_cracking()
        else:
            self.start_cracking()

    def start_cracking(self):
        """Inicia el proceso de cracking"""
        cap_file = self.cap_input.text().strip()
        if not cap_file:
            QMessageBox.warning(self, "Error", "Seleccione un archivo de captura")
            return

        if not os.path.exists(cap_file):
            QMessageBox.warning(self, "Error", f"Archivo no encontrado: {cap_file}")
            return

        wordlist = self.wordlist_input.text().strip()
        if not wordlist:
            QMessageBox.warning(self, "Error", "Seleccione un wordlist")
            return

        if not os.path.exists(wordlist):
            QMessageBox.warning(self, "Error", f"Wordlist no encontrado: {wordlist}")
            return

        bssid = self.bssid_input.text().strip()
        tool = self.tool_combo.currentData()

        reply = QMessageBox.question(
            self,
            "Confirmar Cracking",
            f"Iniciar cracking con {tool}?\n\n"
            f"Archivo: {cap_file}\n"
            f"Wordlist: {wordlist}\n"
            f"BSSID: {bssid or 'Auto-detectar'}\n",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.is_cracking = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("Crackeando...")
        self.progress.setRange(0, 0)  # Indeterminate
        self.crack_log.clear()

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.crack_log.append(f"[{timestamp}] Iniciando cracking con {tool}")
        self.crack_log.append(f"Archivo: {cap_file}")
        self.crack_log.append(f"Wordlist: {wordlist}")

        if tool == "aircrack-ng":
            cmd = ["aircrack-ng", "-w", wordlist]
            if bssid:
                cmd.extend(["-b", bssid])
            cmd.append(cap_file)
        else:
            # hashcat
            cmd = ["hashcat", "-m", "22000", cap_file, wordlist,
                   "--force", "--status", "--status-timer=2"]

        if self.command_runner:
            self.current_cmd_id = self.command_runner.run_command(
                cmd,
                callback=self._on_crack_finished,
                progress_callback=self._on_crack_progress
            )
            self.log_signal.emit(f"Cracking iniciado con {tool}")
        else:
            self.is_cracking = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            QMessageBox.warning(self, "Error", "CommandRunner no disponible")

    def _on_crack_progress(self, cmd_id, line):
        """Callback de progreso de cracking"""
        if cmd_id == self.current_cmd_id:
            self.crack_log.append(line)
            scrollbar = self.crack_log.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _on_crack_finished(self, cmd_id, result):
        """Callback cuando termina el cracking"""
        if cmd_id != self.current_cmd_id:
            return

        self.is_cracking = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setRange(0, 100)

        output = result.stdout if hasattr(result, 'stdout') else str(result)

        # Buscar password en la salida de aircrack-ng
        password = None
        if "KEY FOUND!" in output:
            for line in output.split('\n'):
                if "KEY FOUND!" in line:
                    # Extraer password entre corchetes
                    start = line.find('[')
                    end = line.find(']', start)
                    if start != -1 and end != -1:
                        password = line[start + 1:end].strip()
                    break

        if password:
            self.status_label.setText(f"PASSWORD ENCONTRADA: {password}")
            self.status_label.setStyleSheet("color: green;")
            self.progress.setValue(100)
            self.crack_log.append(f"\nPASSWORD ENCONTRADA: {password}")
            self.log_signal.emit(f"Password crackeada: {password}")

            # Guardar en BD
            if self.db:
                bssid = self.bssid_input.text().strip()
                if bssid:
                    network = self.db.get_network_by_bssid(bssid)
                    if network:
                        handshakes = self.db.get_handshakes_by_network(network['id'])
                        if handshakes:
                            self.db.update_handshake_cracked(
                                handshakes[0]['id'], password,
                                self.wordlist_input.text().strip()
                            )
                self.refresh_handshakes()
        else:
            self.status_label.setText("Password no encontrada")
            self.status_label.setStyleSheet("color: orange;")
            self.progress.setValue(100)
            self.crack_log.append("\nPassword no encontrada en el wordlist")
            self.log_signal.emit("Cracking finalizado sin resultado")

    def stop_cracking(self):
        """Detiene el proceso de cracking"""
        if self.current_cmd_id and self.command_runner:
            self.command_runner.cancel_command(self.current_cmd_id)

        self.is_cracking = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Detenido")
        self.status_label.setStyleSheet("")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.crack_log.append("Cracking detenido por el usuario")
        self.log_signal.emit("Cracking detenido")

    def on_command_finished(self, cmd_id, result):
        """Maneja señal global de comando terminado"""
        pass

    def on_command_progress(self, cmd_id, line):
        """Maneja señal global de progreso"""
        pass
