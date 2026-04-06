#!/usr/bin/env python3
"""
WifiPwn - Database Manager (sin PyQt5)
"""

import sqlite3
import json
import threading
from datetime import datetime
from typing import List, Dict, Optional, Callable
from pathlib import Path
from contextlib import contextmanager
import os


class DatabaseManager:
    _instance: Optional["DatabaseManager"] = None
    _init_lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._initialized = False
                    cls._instance = inst
        return cls._instance

    def __init__(self, db_path: str = None):
        if self._initialized:
            return

        in_docker = os.path.exists("/.dockerenv")
        if db_path is None:
            if in_docker:
                db_path = "/app/data/wifipwn.db"
            else:
                root = Path(__file__).parent.parent.parent
                db_path = str(root / "data" / "wifipwn.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._change_cbs: List[Callable] = []
        self._init_db()
        self._initialized = True

    # ------------------------------------------------------------------
    # Change notification
    # ------------------------------------------------------------------

    def on_change(self, cb: Callable):
        self._change_cbs.append(cb)

    def _notify(self, table: str):
        for cb in self._change_cbs:
            try:
                cb(table)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def cursor(self):
        conn = self._conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_db(self):
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
            last_seen  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        CREATE INDEX IF NOT EXISTS idx_handshakes_net  ON handshakes(network_id);
        CREATE INDEX IF NOT EXISTS idx_creds_date      ON credentials(capture_date);
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript(schema)
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Networks
    # ------------------------------------------------------------------

    def upsert_network(self, bssid: str, essid: str = None, channel: int = None,
                       security: str = None, cipher: str = None,
                       authentication: str = None, power: int = None) -> int:
        with self.cursor() as cur:
            cur.execute("SELECT id FROM networks WHERE bssid=?", (bssid,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    """UPDATE networks SET essid=?,channel=?,security=?,cipher=?,
                       authentication=?,power=?,last_seen=CURRENT_TIMESTAMP WHERE id=?""",
                    (essid, channel, security, cipher, authentication, power, row["id"]),
                )
                nid = row["id"]
            else:
                cur.execute(
                    """INSERT INTO networks (bssid,essid,channel,security,cipher,authentication,power)
                       VALUES (?,?,?,?,?,?,?)""",
                    (bssid, essid, channel, security, cipher, authentication, power),
                )
                nid = cur.lastrowid
        self._notify("networks")
        return nid

    def get_networks(self) -> List[Dict]:
        with self.cursor() as cur:
            cur.execute("""
                SELECT n.*,
                       COUNT(h.id) as handshake_count,
                       SUM(CASE WHEN h.cracked=1 THEN 1 ELSE 0 END) as cracked_count
                FROM networks n
                LEFT JOIN handshakes h ON n.id=h.network_id
                GROUP BY n.id ORDER BY n.last_seen DESC
            """)
            return [dict(r) for r in cur.fetchall()]

    def get_network_by_bssid(self, bssid: str) -> Optional[Dict]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM networks WHERE bssid=?", (bssid,))
            r = cur.fetchone()
            return dict(r) if r else None

    # ------------------------------------------------------------------
    # Handshakes
    # ------------------------------------------------------------------

    def add_handshake(self, network_id: int, capture_file: str) -> int:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO handshakes (network_id,capture_file) VALUES (?,?)",
                (network_id, capture_file),
            )
            hid = cur.lastrowid
        self._notify("handshakes")
        return hid

    def crack_handshake(self, handshake_id: int, password: str, wordlist: str = None):
        with self.cursor() as cur:
            cur.execute(
                "UPDATE handshakes SET cracked=1,password=?,wordlist_used=? WHERE id=?",
                (password, wordlist, handshake_id),
            )
        self._notify("handshakes")

    def get_handshakes(self, network_id: int = None) -> List[Dict]:
        with self.cursor() as cur:
            if network_id:
                cur.execute(
                    "SELECT * FROM handshakes WHERE network_id=? ORDER BY capture_date DESC",
                    (network_id,),
                )
            else:
                cur.execute("""
                    SELECT h.*, n.bssid, n.essid
                    FROM handshakes h
                    LEFT JOIN networks n ON h.network_id=n.id
                    ORDER BY h.capture_date DESC
                """)
            return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    def add_credential(self, source: str, username: str, password: str,
                       ip_address: str = None, network_id: int = None) -> int:
        with self.cursor() as cur:
            cur.execute(
                """INSERT INTO credentials (source,username,password,ip_address,network_id)
                   VALUES (?,?,?,?,?)""",
                (source, username, password, ip_address, network_id),
            )
            cid = cur.lastrowid
        self._notify("credentials")
        return cid

    def get_credentials(self, limit: int = 100) -> List[Dict]:
        with self.cursor() as cur:
            cur.execute("""
                SELECT c.*, n.bssid, n.essid
                FROM credentials c
                LEFT JOIN networks n ON c.network_id=n.id
                ORDER BY c.capture_date DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Campaigns
    # ------------------------------------------------------------------

    def create_campaign(self, name: str, description: str = "") -> int:
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO campaigns (name,description) VALUES (?,?)",
                (name, description),
            )
            return cur.lastrowid

    def get_campaigns(self) -> List[Dict]:
        with self.cursor() as cur:
            cur.execute("""
                SELECT c.*,
                       COUNT(ct.id) as target_count,
                       SUM(CASE WHEN ct.status='completed' THEN 1 ELSE 0 END) as completed_count
                FROM campaigns c
                LEFT JOIN campaign_targets ct ON c.id=ct.campaign_id
                GROUP BY c.id ORDER BY c.created_date DESC
            """)
            return [dict(r) for r in cur.fetchall()]

    def update_campaign(self, campaign_id: int, name: str = None,
                        description: str = None, status: str = None):
        with self.cursor() as cur:
            if name:
                cur.execute("UPDATE campaigns SET name=?,updated_date=CURRENT_TIMESTAMP WHERE id=?",
                            (name, campaign_id))
            if description is not None:
                cur.execute("UPDATE campaigns SET description=?,updated_date=CURRENT_TIMESTAMP WHERE id=?",
                            (description, campaign_id))
            if status:
                cur.execute("UPDATE campaigns SET status=?,updated_date=CURRENT_TIMESTAMP WHERE id=?",
                            (status, campaign_id))

    def delete_campaign(self, campaign_id: int):
        with self.cursor() as cur:
            cur.execute("DELETE FROM campaign_targets WHERE campaign_id=?", (campaign_id,))
            cur.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))

    def add_campaign_target(self, campaign_id: int, network_id: int, notes: str = ""):
        with self.cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO campaign_targets (campaign_id,network_id,notes) VALUES (?,?,?)",
                (campaign_id, network_id, notes),
            )

    def get_campaign_targets(self, campaign_id: int) -> List[Dict]:
        with self.cursor() as cur:
            cur.execute("""
                SELECT ct.*, n.bssid, n.essid, n.channel, n.security
                FROM campaign_targets ct
                JOIN networks n ON ct.network_id=n.id
                WHERE ct.campaign_id=?
            """, (campaign_id,))
            return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Deauth
    # ------------------------------------------------------------------

    def log_deauth(self, network_id: int, client_mac: str = None, packets: int = 0):
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO deauth_attacks (network_id,client_mac,packets_sent) VALUES (?,?,?)",
                (network_id, client_mac, packets),
            )
        self._notify("deauth_attacks")

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    def log_action(self, action: str, details: str = None, success: bool = True):
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO audit_logs (action,details,success) VALUES (?,?,?)",
                (action, details, 1 if success else 0),
            )

    def get_recent_logs(self, limit: int = 50) -> List[Dict]:
        with self.cursor() as cur:
            cur.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_statistics(self) -> Dict:
        with self.cursor() as cur:
            def count(q):
                cur.execute(q)
                return cur.fetchone()[0]

            return {
                "total_networks":    count("SELECT COUNT(*) FROM networks"),
                "total_handshakes":  count("SELECT COUNT(*) FROM handshakes"),
                "cracked_handshakes": count("SELECT COUNT(*) FROM handshakes WHERE cracked=1"),
                "total_credentials": count("SELECT COUNT(*) FROM credentials"),
                "total_campaigns":   count("SELECT COUNT(*) FROM campaigns"),
                "total_deauth":      count("SELECT COUNT(*) FROM deauth_attacks"),
            }

    # ------------------------------------------------------------------
    # Bulk
    # ------------------------------------------------------------------

    def clear_table(self, table: str) -> bool:
        allowed = {"networks","handshakes","credentials","campaigns",
                   "deauth_attacks","audit_logs"}
        if table not in allowed:
            return False
        with self.cursor() as cur:
            cur.execute(f"DELETE FROM {table}")
        self._notify(table)
        return True

    def clear_all(self) -> bool:
        try:
            with self.cursor() as cur:
                for t in ["campaign_targets","campaigns","deauth_attacks",
                          "credentials","handshakes","networks","audit_logs"]:
                    cur.execute(f"DELETE FROM {t}")
            self._notify("all")
            return True
        except Exception:
            return False

    def export_json(self, filepath: str):
        data = {
            "networks":     self.get_networks(),
            "handshakes":   self.get_handshakes(),
            "credentials":  self.get_credentials(10000),
            "campaigns":    self.get_campaigns(),
            "statistics":   self.get_statistics(),
            "exported_at":  datetime.now().isoformat(),
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


db = DatabaseManager()
