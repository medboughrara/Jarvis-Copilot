"""
Unified Scoped Memory Manager for Jarvis Copilot.
Directly adapts affaan-m/ECC Unified Memory architecture:
- User Scope: Operator preferences, favorite voices, developer conventions.
- Project Scope: Repository architecture, active schematics, hardware components, sprint deliverables.
- Session Scope: Ephemeral multi-turn context and follow-up memory.
"""

import os
import time
import json
import sqlite3
from typing import Dict, Any, List, Optional
import config

logger = config.get_logger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory.db")

class UnifiedScopedMemory:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()
        self.session_memory: Dict[str, Any] = {}

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scoped_memory (
                    scope TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    metadata TEXT,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (scope, key)
                )
            """)
            conn.commit()

    def set(self, scope: str, key: str, value: Any, metadata: Dict[str, Any] = None):
        scope = scope.lower().strip()
        if scope not in ["user", "project", "session"]:
            scope = "project"

        if scope == "session":
            self.session_memory[key] = {
                "value": value,
                "metadata": metadata or {},
                "updated_at": time.time()
            }
            return

        val_str = json.dumps(value) if not isinstance(value, str) else value
        meta_str = json.dumps(metadata or {})
        now = time.time()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO scoped_memory (scope, key, value, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (scope, key, val_str, meta_str, now))
            conn.commit()

    def get(self, scope: str, key: str, default: Any = None) -> Any:
        scope = scope.lower().strip()
        if scope == "session":
            return self.session_memory.get(key, {}).get("value", default)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT value FROM scoped_memory WHERE scope = ? AND key = ?
            """, (scope, key))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except Exception:
                    return row[0]
            return default

    def list_scope(self, scope: str) -> List[Dict[str, Any]]:
        scope = scope.lower().strip()
        if scope == "session":
            return [
                {"key": k, "value": v["value"], "metadata": v["metadata"], "updated_at": v["updated_at"]}
                for k, v in self.session_memory.items()
            ]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT key, value, metadata, updated_at FROM scoped_memory WHERE scope = ? ORDER BY updated_at DESC
            """, (scope,))
            results = []
            for row in cursor.fetchall():
                try:
                    val = json.loads(row[1])
                except Exception:
                    val = row[1]
                try:
                    meta = json.loads(row[2])
                except Exception:
                    meta = {}
                results.append({
                    "key": row[0],
                    "value": val,
                    "metadata": meta,
                    "updated_at": row[3]
                })
            return results


# Global Singleton Unified Memory
unified_memory = UnifiedScopedMemory()
