#!/usr/bin/env python3
"""
WifiPwn - Modulo de Base de Datos SQLite
Gestiona el almacenamiento persistente de datos
"""

import sqlite3
import json
import os
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
from contextlib import contextmanager
from PyQt5.QtCore import QObject, pyqtSignal


class DatabaseManager(QObject):
    """Gestor de base de datos SQLite para WifiPwn"""
    
    network_added = pyqtSignal(int)
    handshake_added = pyqtSignal(int)
    credential_added = pyqtSignal(int)
    data_changed = pyqtSignal(str)
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = None):
        if self._initialized:
            return
            
        super().__init__()
        
        # Detectar si estamos en Docker
        in_docker = os.path.exists('/.dockerenv')
        
        if db_path is None:
            if in_docker:
                db_path = "/app/data/wifipwn.db"
            else:
                # En el host, usar ruta relativa al script
                script_dir = Path(__file__).parent.parent.parent
                db_path = str(script_dir / "data" / "wifipwn.db")
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.init_database()
        self._initialized = True
    
    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(self.db_path))
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def init_database(self):
        schema = """
        CREATE TABLE IF NOT EXISTS networks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bssid TEXT UNIQUE NOT NULL,
            essid TEXT,
            channel INTEGER,
            security TEXT,
            cipher TEXT,
            authentication TEXT,
            power INTEGER,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            latitude REAL,
            longitude REAL,
            notes TEXT,
            wps_enabled INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS handshakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_id INTEGER,
            capture_file TEXT NOT NULL,
            capture_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cracked INTEGER DEFAULT 0,
            password TEXT,
            wordlist_used TEXT,
            FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            username TEXT,
            password TEXT,
            capture_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            network_id INTEGER,
            FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        );

        CREATE TABLE IF NOT EXISTS campaign_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            network_id INTEGER,
            status TEXT DEFAULT 'pending',
            notes TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
            FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS deauth_attacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_id INTEGER,
            client_mac TEXT,
            packets_sent INTEGER,
            attack_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_networks_bssid ON networks(bssid);
        CREATE INDEX IF NOT EXISTS idx_handshakes_network ON handshakes(network_id);
        CREATE INDEX IF NOT EXISTS idx_credentials_date ON credentials(capture_date);
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript(schema)
        conn.commit()
        conn.close()
    
    def add_or_update_network(self, bssid: str, essid: str = None, 
                              channel: int = None, security: str = None,
                              cipher: str = None, power: int = None) -> int:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT id FROM networks WHERE bssid = ?", (bssid,))
            result = cursor.fetchone()
            
            if result:
                network_id = result['id']
                cursor.execute("""
                    UPDATE networks SET essid = ?, channel = ?, security = ?,
                    cipher = ?, power = ?, last_seen = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (essid, channel, security, cipher, power, network_id))
            else:
                cursor.execute("""
                    INSERT INTO networks (bssid, essid, channel, security, cipher, power)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (bssid, essid, channel, security, cipher, power))
                network_id = cursor.lastrowid
                self.network_added.emit(network_id)
            
            self.data_changed.emit('networks')
            return network_id
    
    def get_all_networks(self) -> List[Dict]:
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT n.*, COUNT(h.id) as handshake_count,
                SUM(CASE WHEN h.cracked = 1 THEN 1 ELSE 0 END) as cracked_count
                FROM networks n
                LEFT JOIN handshakes h ON n.id = h.network_id
                GROUP BY n.id
                ORDER BY n.last_seen DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_network_by_bssid(self, bssid: str) -> Optional[Dict]:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT * FROM networks WHERE bssid = ?", (bssid,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def add_handshake(self, network_id: int, capture_file: str) -> int:
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO handshakes (network_id, capture_file)
                VALUES (?, ?)
            """, (network_id, capture_file))
            handshake_id = cursor.lastrowid
            self.handshake_added.emit(handshake_id)
            self.data_changed.emit('handshakes')
            return handshake_id
    
    def update_handshake_cracked(self, handshake_id: int, password: str, 
                                  wordlist: str = None):
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE handshakes 
                SET cracked = 1, password = ?, wordlist_used = ?
                WHERE id = ?
            """, (password, wordlist, handshake_id))
            self.data_changed.emit('handshakes')
    
    def get_handshakes_by_network(self, network_id: int) -> List[Dict]:
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM handshakes WHERE network_id = ?
                ORDER BY capture_date DESC
            """, (network_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def add_credential(self, source: str, username: str, password: str,
                       ip_address: str = None, network_id: int = None) -> int:
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO credentials (source, username, password, ip_address, network_id)
                VALUES (?, ?, ?, ?, ?)
            """, (source, username, password, ip_address, network_id))
            cred_id = cursor.lastrowid
            self.credential_added.emit(cred_id)
            self.data_changed.emit('credentials')
            return cred_id
    
    def get_all_credentials(self, limit: int = 100) -> List[Dict]:
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT c.*, n.bssid, n.essid 
                FROM credentials c
                LEFT JOIN networks n ON c.network_id = n.id
                ORDER BY c.capture_date DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def add_campaign(self, name: str, description: str = "") -> int:
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO campaigns (name, description)
                VALUES (?, ?)
            """, (name, description))
            return cursor.lastrowid
    
    def get_all_campaigns(self) -> List[Dict]:
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT c.*, 
                    COUNT(ct.id) as target_count,
                    SUM(CASE WHEN ct.status = 'completed' THEN 1 ELSE 0 END) as completed_count
                FROM campaigns c
                LEFT JOIN campaign_targets ct ON c.id = ct.campaign_id
                GROUP BY c.id
                ORDER BY c.created_date DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_campaign_target(self, campaign_id: int, network_id: int, notes: str = ""):
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT OR IGNORE INTO campaign_targets (campaign_id, network_id, notes)
                VALUES (?, ?, ?)
            """, (campaign_id, network_id, notes))
    
    def log_action(self, action: str, details: str = None, success: bool = True):
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO audit_logs (action, details, success)
                VALUES (?, ?, ?)
            """, (action, details, 1 if success else 0))
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM audit_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def add_deauth_attack(self, network_id: int, client_mac: str = None, 
                          packets_sent: int = 0):
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO deauth_attacks (network_id, client_mac, packets_sent)
                VALUES (?, ?, ?)
            """, (network_id, client_mac, packets_sent))
    
    def get_statistics(self) -> Dict:
        with self.get_cursor() as cursor:
            stats = {}
            
            cursor.execute("SELECT COUNT(*) as count FROM networks")
            stats['total_networks'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM handshakes")
            stats['total_handshakes'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM handshakes WHERE cracked = 1")
            stats['cracked_handshakes'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM credentials")
            stats['total_credentials'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM campaigns")
            stats['total_campaigns'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM deauth_attacks")
            stats['total_deauth_attacks'] = cursor.fetchone()['count']
            
            return stats
    
    def clear_all_data(self) -> bool:
        """Limpia todas las tablas de la base de datos"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM campaign_targets")
                cursor.execute("DELETE FROM campaigns")
                cursor.execute("DELETE FROM deauth_attacks")
                cursor.execute("DELETE FROM credentials")
                cursor.execute("DELETE FROM handshakes")
                cursor.execute("DELETE FROM networks")
                cursor.execute("DELETE FROM audit_logs")
                cursor.execute("VACUUM")
            self.data_changed.emit('all')
            return True
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False
    
    def clear_table(self, table_name: str) -> bool:
        """Limpia una tabla específica"""
        allowed_tables = ['networks', 'handshakes', 'credentials', 'campaigns',
                         'deauth_attacks', 'audit_logs']
        
        if table_name not in allowed_tables:
            return False
        
        try:
            with self.get_cursor() as cursor:
                cursor.execute(f"DELETE FROM {table_name}")
            self.data_changed.emit(table_name)
            return True
        except Exception as e:
            print(f"Error clearing table {table_name}: {e}")
            return False
    
    def search_networks(self, query: str) -> List[Dict]:
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM networks
                WHERE bssid LIKE ? OR essid LIKE ?
                ORDER BY last_seen DESC
            """, (f"%{query}%", f"%{query}%"))
            return [dict(row) for row in cursor.fetchall()]
    
    def export_to_json(self, filepath: str):
        """Exporta toda la base de datos a JSON"""
        data = {
            'networks': self.get_all_networks(),
            'credentials': self.get_all_credentials(limit=10000),
            'campaigns': self.get_all_campaigns(),
            'statistics': self.get_statistics(),
            'exported_at': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
