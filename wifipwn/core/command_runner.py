#!/usr/bin/env python3
"""
WifiPwn - Ejecutor de Comandos en Background
Gestiona la ejecución asíncrona de comandos del sistema
"""

import subprocess
import threading
import queue
import time
import re
from typing import List, Dict, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool


class CommandStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    duration: float
    status: CommandStatus


class CommandWorker(QRunnable):
    """Worker para ejecutar comandos en el thread pool"""
    
    def __init__(self, cmd_id: str, command: List[str], 
                 callback: Callable = None,
                 progress_callback: Callable = None,
                 realtime_output: bool = True):
        super().__init__()
        self.cmd_id = cmd_id
        self.command = command
        self.callback = callback
        self.progress_callback = progress_callback
        self.realtime_output = realtime_output
        self._cancelled = False
        self.process: Optional[subprocess.Popen] = None
    
    def run(self):
        start_time = time.time()
        stdout_lines = []
        stderr_lines = []
        
        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Leer stdout en tiempo real
            if self.realtime_output and self.progress_callback:
                for line in iter(self.process.stdout.readline, ''):
                    if self._cancelled:
                        self.process.terminate()
                        break
                    if line:
                        stdout_lines.append(line)
                        self.progress_callback(self.cmd_id, line.strip())
            else:
                stdout, stderr = self.process.communicate()
                stdout_lines = stdout.split('\n') if stdout else []
                stderr_lines = stderr.split('\n') if stderr else []
            
            if not self._cancelled:
                self.process.wait()
            
            duration = time.time() - start_time
            
            result = CommandResult(
                command=' '.join(self.command),
                returncode=self.process.returncode if not self._cancelled else -1,
                stdout='\n'.join(stdout_lines),
                stderr='\n'.join(stderr_lines),
                duration=duration,
                status=CommandStatus.CANCELLED if self._cancelled else 
                       (CommandStatus.COMPLETED if self.process.returncode == 0 else CommandStatus.FAILED)
            )
            
        except Exception as e:
            duration = time.time() - start_time
            result = CommandResult(
                command=' '.join(self.command),
                returncode=-1,
                stdout='',
                stderr=str(e),
                duration=duration,
                status=CommandStatus.FAILED
            )
        
        if self.callback:
            self.callback(self.cmd_id, result)
    
    def cancel(self):
        self._cancelled = True
        if self.process:
            self.process.terminate()


class CommandRunner(QObject):
    """Gestor centralizado de ejecución de comandos"""
    
    command_started = pyqtSignal(str, str)  # cmd_id, command
    command_finished = pyqtSignal(str, object)  # cmd_id, result
    command_progress = pyqtSignal(str, str)  # cmd_id, line
    command_error = pyqtSignal(str, str)  # cmd_id, error
    
    def __init__(self, max_threads: int = 10):
        super().__init__()
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(max_threads)
        self.active_commands: Dict[str, CommandWorker] = {}
        self.command_history: List[Dict] = []
        self._lock = threading.Lock()
        self._counter = 0
    
    def _generate_id(self) -> str:
        with self._lock:
            self._counter += 1
            return f"cmd_{self._counter}_{int(time.time())}"
    
    def run_command(self, command: List[str], 
                   callback: Callable = None,
                   progress_callback: Callable = None,
                   cmd_id: str = None) -> str:
        """
        Ejecuta un comando en background
        
        Args:
            command: Lista con el comando y argumentos
            callback: Función a llamar al terminar
            progress_callback: Función para recibir output en tiempo real
            cmd_id: ID opcional para el comando
            
        Returns:
            ID del comando
        """
        if cmd_id is None:
            cmd_id = self._generate_id()
        
        # Crear wrapper para los callbacks
        def wrapper_callback(cid, result):
            self.command_finished.emit(cid, result)
            if callback:
                callback(cid, result)
            with self._lock:
                if cid in self.active_commands:
                    del self.active_commands[cid]
        
        def wrapper_progress(cid, line):
            self.command_progress.emit(cid, line)
            if progress_callback:
                progress_callback(cid, line)
        
        worker = CommandWorker(
            cmd_id=cmd_id,
            command=command,
            callback=wrapper_callback,
            progress_callback=wrapper_progress
        )
        
        with self._lock:
            self.active_commands[cmd_id] = worker
        
        self.command_started.emit(cmd_id, ' '.join(command))
        self.threadpool.start(worker)
        
        # Guardar en historial
        self.command_history.append({
            'id': cmd_id,
            'command': ' '.join(command),
            'start_time': time.time(),
            'status': CommandStatus.RUNNING
        })
        
        return cmd_id
    
    def cancel_command(self, cmd_id: str) -> bool:
        """Cancela un comando en ejecución"""
        with self._lock:
            if cmd_id in self.active_commands:
                self.active_commands[cmd_id].cancel()
                return True
        return False
    
    def cancel_all(self):
        """Cancela todos los comandos activos"""
        with self._lock:
            for worker in self.active_commands.values():
                worker.cancel()
            self.active_commands.clear()
    
    def is_running(self, cmd_id: str) -> bool:
        """Verifica si un comando está en ejecución"""
        with self._lock:
            return cmd_id in self.active_commands
    
    def get_active_commands(self) -> List[str]:
        """Retorna lista de IDs de comandos activos"""
        with self._lock:
            return list(self.active_commands.keys())
    
    def get_history(self) -> List[Dict]:
        """Retorna historial de comandos"""
        return self.command_history.copy()
    
    # ==================== COMANDOS ESPECÍFICOS ====================
    
    def scan_networks(self, interface: str, callback: Callable = None) -> str:
        """Inicia escaneo de redes con airodump-ng"""
        cmd = [
            "airodump-ng",
            "--write-interval", "1",
            "--write", "/tmp/scan",
            "--output-format", "csv",
            interface
        ]
        return self.run_command(cmd, callback)
    
    def capture_handshake(self, interface: str, bssid: str, 
                         channel: int, output: str,
                         callback: Callable = None) -> str:
        """Inicia captura de handshake"""
        cmd = [
            "airodump-ng",
            "--channel", str(channel),
            "--bssid", bssid,
            "--write", output,
            interface
        ]
        return self.run_command(cmd, callback)
    
    def deauth_attack(self, interface: str, bssid: str,
                     client: str = None, packets: int = 10,
                     callback: Callable = None) -> str:
        """Envía paquetes de deautenticación"""
        cmd = [
            "aireplay-ng",
            "-0", str(packets),
            "-a", bssid
        ]
        if client:
            cmd.extend(["-c", client])
        cmd.append(interface)
        
        return self.run_command(cmd, callback)
    
    def crack_handshake(self, cap_file: str, bssid: str,
                       wordlist: str, callback: Callable = None,
                       progress_callback: Callable = None) -> str:
        """Inicia cracking con aircrack-ng"""
        cmd = [
            "aircrack-ng",
            "-w", wordlist,
            "-b", bssid,
            cap_file
        ]
        return self.run_command(cmd, callback, progress_callback)
    
    def enable_monitor_mode(self, interface: str, 
                           callback: Callable = None) -> str:
        """Activa modo monitor"""
        cmd = ["airmon-ng", "start", interface]
        return self.run_command(cmd, callback)
    
    def disable_monitor_mode(self, interface: str,
                            callback: Callable = None) -> str:
        """Desactiva modo monitor"""
        cmd = ["airmon-ng", "stop", interface]
        return self.run_command(cmd, callback)
    
    def check_handshake(self, cap_file: str, 
                       callback: Callable = None) -> str:
        """Verifica si un archivo contiene handshake"""
        cmd = ["aircrack-ng", cap_file]
        return self.run_command(cmd, callback)
