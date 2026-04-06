#!/usr/bin/env python3
"""
WifiPwn - Command Runner (sin dependencias PyQt5)
Ejecuta comandos en background con streaming de output via callbacks/WebSocket
"""

import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


class ProcessStatus(Enum):
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessInfo:
    cmd_id:      str
    command:     List[str]
    status:      ProcessStatus = ProcessStatus.RUNNING
    output_lines: List[str]   = field(default_factory=list)
    returncode:  Optional[int] = None
    start_time:  float         = field(default_factory=time.time)
    end_time:    Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "cmd_id":      self.cmd_id,
            "command":     " ".join(self.command),
            "status":      self.status.value,
            "returncode":  self.returncode,
            "start_time":  self.start_time,
            "end_time":    self.end_time,
            "lines":       len(self.output_lines),
        }


class CommandManager:
    """Singleton que gestiona todos los procesos en background."""

    _instance: Optional["CommandManager"] = None
    _init_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._processes:  Dict[str, ProcessInfo]           = {}
        self._handles:    Dict[str, subprocess.Popen]       = {}
        self._callbacks:  Dict[str, List[Callable]]         = {}
        self._global_out_cbs: List[Callable]                = []
        self._lock        = threading.Lock()
        self._initialized = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        command: List[str],
        on_output:  Callable = None,   # fn(cmd_id, line)
        on_finish:  Callable = None,   # fn(cmd_id, info)
    ) -> str:
        """Ejecuta comando en un thread. Devuelve cmd_id."""
        cmd_id = uuid.uuid4().hex[:8]
        info   = ProcessInfo(cmd_id=cmd_id, command=command)

        with self._lock:
            self._processes[cmd_id] = info
            self._callbacks[cmd_id] = []
        if on_output:
            self._callbacks[cmd_id].append(on_output)

        t = threading.Thread(
            target=self._worker,
            args=(cmd_id, command, on_finish),
            daemon=True,
        )
        t.start()
        return cmd_id

    def subscribe_output(self, cmd_id: str, callback: Callable):
        """Suscribe un callback al output de un proceso en ejecución."""
        with self._lock:
            if cmd_id in self._callbacks:
                self._callbacks[cmd_id].append(callback)

    def subscribe_global(self, callback: Callable):
        """Suscribe callback a TODO output de cualquier proceso."""
        self._global_out_cbs.append(callback)

    def cancel(self, cmd_id: str) -> bool:
        with self._lock:
            proc = self._handles.get(cmd_id)
            if proc and proc.poll() is None:
                proc.terminate()
                if cmd_id in self._processes:
                    self._processes[cmd_id].status = ProcessStatus.CANCELLED
                return True
        return False

    def cancel_all(self):
        with self._lock:
            ids = list(self._handles.keys())
        for cmd_id in ids:
            self.cancel(cmd_id)

    def is_running(self, cmd_id: str) -> bool:
        with self._lock:
            info = self._processes.get(cmd_id)
            return info is not None and info.status == ProcessStatus.RUNNING

    def get_output(self, cmd_id: str) -> List[str]:
        with self._lock:
            info = self._processes.get(cmd_id)
            return list(info.output_lines) if info else []

    def get_info(self, cmd_id: str) -> Optional[ProcessInfo]:
        with self._lock:
            return self._processes.get(cmd_id)

    def list_all(self) -> List[dict]:
        with self._lock:
            return [v.to_dict() for v in self._processes.values()]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _worker(self, cmd_id: str, command: List[str], on_finish: Callable):
        try:
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            with self._lock:
                self._handles[cmd_id] = proc

            for raw in iter(proc.stdout.readline, ""):
                line = raw.rstrip("\n")
                if not line:
                    continue

                with self._lock:
                    info = self._processes.get(cmd_id)
                    if info:
                        info.output_lines.append(line)
                    cbs       = list(self._callbacks.get(cmd_id, []))
                    global_cbs = list(self._global_out_cbs)

                for cb in cbs + global_cbs:
                    try:
                        cb(cmd_id, line)
                    except Exception:
                        pass

            proc.wait()

            with self._lock:
                info = self._processes.get(cmd_id)
                if info and info.status == ProcessStatus.RUNNING:
                    info.returncode = proc.returncode
                    info.end_time   = time.time()
                    info.status     = (
                        ProcessStatus.COMPLETED
                        if proc.returncode == 0
                        else ProcessStatus.FAILED
                    )

        except Exception as e:
            with self._lock:
                info = self._processes.get(cmd_id)
                if info:
                    info.status   = ProcessStatus.FAILED
                    info.end_time = time.time()
                    info.output_lines.append(f"[ERROR] {e}")

        if on_finish:
            try:
                on_finish(cmd_id, self.get_info(cmd_id))
            except Exception:
                pass


# Singleton global
command_manager = CommandManager()
