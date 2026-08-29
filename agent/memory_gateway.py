"""
Unified Memory Gateway Facade for Jarvis AI / Jarvis-Copilot.
Consolidates the 4 fragmented memory subsystems behind a single architectural interface:
1. Hierarchical Scored Memory Tree & Kanban Goals (data/memory_tree.db)
2. ECC Unified Scoped Memory: User, Project, Session (data/scoped_memory.db)
3. MemPalace Method-of-Loci Verbatim Long-Term Memory (data/mempalace/)
4. Attention Queue & Context Window Compressor
"""

import os
import time
import json
import sqlite3
from typing import Dict, Any, List, Optional
import config

logger = config.get_logger(__name__)

# Standardized Data Root Directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

SCOPED_DB_PATH = os.path.join(DATA_DIR, "scoped_memory.db")
MEMORY_TREE_DB_PATH = os.path.join(DATA_DIR, "memory_tree.db")
MEMPALACE_DIR = os.path.join(DATA_DIR, "mempalace")
os.makedirs(MEMPALACE_DIR, exist_ok=True)


class MemoryGatewayFacade:
    """Unified Facade for all persistent memory, knowledge nodes, and kanban goals."""

    def __init__(self):
        self._init_databases()

    def _init_databases(self):
        # 1. Scoped Memory Table
        with sqlite3.connect(SCOPED_DB_PATH) as conn:
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

        # 2. Hierarchical Memory Tree Table
        with sqlite3.connect(MEMORY_TREE_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    score REAL DEFAULT 0.5,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kanban_goals (
                    goal_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    deadline TEXT,
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()

    # --- Unified Storage API ---

    def store(self, key: str, value: Any, scope: str = "project", category: str = "general", score: float = 0.5, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Stores a fact across both scoped memory and the scored hierarchical tree."""
        val_str = json.dumps(value) if not isinstance(value, str) else value
        now = time.time()
        meta_str = json.dumps(metadata or {})

        # Save to Scoped Memory
        with sqlite3.connect(SCOPED_DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO scoped_memory (scope, key, value, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (scope.lower(), key, val_str, meta_str, now))
            conn.commit()

        # Save to Memory Tree
        with sqlite3.connect(MEMORY_TREE_DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_nodes (key, value, category, score, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (key, val_str, category, score, now))
            conn.commit()

        return {
            "status": "success",
            "key": key,
            "scope": scope,
            "category": category,
            "score": score
        }

    # --- Unified Retrieval API ---

    def retrieve(self, query: str = "", scope: str = "project", limit: int = 10) -> List[Dict[str, Any]]:
        """Searches unified memory across scopes."""
        results = []
        with sqlite3.connect(SCOPED_DB_PATH) as conn:
            if query:
                cursor = conn.execute("""
                    SELECT key, value, metadata, updated_at FROM scoped_memory 
                    WHERE scope = ? AND (key LIKE ? OR value LIKE ?)
                    ORDER BY updated_at DESC LIMIT ?
                """, (scope.lower(), f"%{query}%", f"%{query}%", limit))
            else:
                cursor = conn.execute("""
                    SELECT key, value, metadata, updated_at FROM scoped_memory 
                    WHERE scope = ? ORDER BY updated_at DESC LIMIT ?
                """, (scope.lower(), limit))

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
                    "updated_at": row[3],
                    "source": f"scoped:{scope}"
                })
        return results

    def get_summary(self) -> Dict[str, Any]:
        """Provides high-level stats of all stored memories across subsystems."""
        with sqlite3.connect(SCOPED_DB_PATH) as conn:
            c_scoped = conn.execute("SELECT COUNT(*) FROM scoped_memory").fetchone()[0]
        with sqlite3.connect(MEMORY_TREE_DB_PATH) as conn:
            c_nodes = conn.execute("SELECT COUNT(*) FROM memory_nodes").fetchone()[0]
            c_goals = conn.execute("SELECT COUNT(*) FROM kanban_goals").fetchone()[0]

        return {
            "scoped_memory_records": c_scoped,
            "hierarchical_nodes_count": c_nodes,
            "kanban_goals_count": c_goals,
            "data_directory": DATA_DIR
        }


# Global Singleton Memory Gateway
memory_gateway = MemoryGatewayFacade()
