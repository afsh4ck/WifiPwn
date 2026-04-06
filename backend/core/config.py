#!/usr/bin/env python3
"""
WifiPwn - Config Manager (sin PyQt5)
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    _instance: Optional["ConfigManager"] = None

    def __new__(cls, config_file: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_file: str = None):
        if self._initialized:
            return

        in_docker = os.path.exists("/.dockerenv")

        if in_docker:
            default_capture = "/app/captures"
            default_reports = "/app/reports"
            default_logs    = "/app/logs"
        else:
            root = Path(__file__).parent.parent.parent
            default_capture = str(root / "captures")
            default_reports = str(root / "reports")
            default_logs    = str(root / "logs")

        self.DEFAULT_CONFIG: Dict[str, Any] = {
            "theme": "dark",
            "language": "es",
            "capture_directory": default_capture,
            "reports_directory": default_reports,
            "logs_directory":    default_logs,
            "default_wordlist":  "/usr/share/wordlists/rockyou.txt",
            "default_interface": "",
            "auto_save_captures": True,
            "scan_timeout": 60,
            "deauth_packets": 10,
        }

        if config_file is None:
            cfg_dir = Path.home() / ".config" / "wifipwn"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = cfg_dir / "config.json"
        else:
            self.config_file = Path(config_file)

        self.config: Dict[str, Any] = {}
        self.load()
        self.ensure_dirs()
        self._initialized = True

    def load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.config = {**self.DEFAULT_CONFIG, **loaded}
            except Exception:
                self.config = dict(self.DEFAULT_CONFIG)
        else:
            self.config = dict(self.DEFAULT_CONFIG)
            self.save()

    def save(self) -> bool:
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        self.config[key] = value

    def ensure_dirs(self):
        for key in ("capture_directory", "reports_directory", "logs_directory"):
            d = self.config.get(key)
            if d:
                Path(d).mkdir(parents=True, exist_ok=True)

    def get_capture_path(self, filename: str = "") -> Path:
        base = Path(self.get("capture_directory"))
        return base / filename if filename else base

    def get_report_path(self, filename: str = "") -> Path:
        base = Path(self.get("reports_directory"))
        return base / filename if filename else base
