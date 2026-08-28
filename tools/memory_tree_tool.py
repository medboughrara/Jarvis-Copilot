"""
Memory Tree & Goals Kanban Engine for Jarvis AI Assistant.
Inspired by OpenHuman's hierarchical scored Memory Tree and Karpathy's LLM Knowledgebase.

Features:
- Hierarchical tree structure (/personal, /projects, /people, /preferences, /research, /pcb_hardware)
- Scored memory nodes (importance, access count, last accessed timestamp, semantic tags)
- Integrated Goals & Todos Kanban board (todo, in_progress, done, blocked) with priority and deadlines
- People Profile dossier memory (contacts, relations, preferences, expertise)
- Automatic markdown sync into the local Obsidian Vault
"""

import os
import json
import sqlite3
import datetime
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scratch", "jarvis_memory_tree.db")
OBSIDIAN_VAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "obsidian_vault", "Memory_Tree")


def _get_db() -> sqlite3.Connection:
    """Initializes and returns SQLite connection with schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                tags TEXT,
                importance INTEGER DEFAULT 5,
                access_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL CHECK(status IN ('todo', 'in_progress', 'done', 'blocked')),
                priority TEXT NOT NULL CHECK(priority IN ('low', 'medium', 'high', 'urgent')),
                category TEXT NOT NULL,
                deadline TEXT,
                progress INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS people_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                role_affiliation TEXT,
                email TEXT,
                phone TEXT,
                notes TEXT,
                tags TEXT,
                updated_at TEXT NOT NULL
            )
        """)
    return conn


def _sync_node_to_obsidian(path: str, title: str, category: str, content: str, tags: str) -> None:
    """Mirrors a memory node to the Obsidian Vault as a Markdown note."""
    try:
        clean_rel = path.strip("/").replace("/", os.sep)
        target_dir = os.path.join(OBSIDIAN_VAULT_PATH, os.path.dirname(clean_rel))
        os.makedirs(target_dir, exist_ok=True)
        filename = f"{os.path.basename(clean_rel)}.md"
        filepath = os.path.join(target_dir, filename)

        md = f"""---
title: "{title}"
category: "{category}"
tags: [{tags}]
synced_at: "{datetime.datetime.now().isoformat()}"
---

# 🧠 {title}

**Path**: `{path}`  
**Category**: `{category}`  
**Tags**: {tags}  

---

{content}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)
    except Exception as e:
        logger.warning(f"[MemoryTree] Obsidian mirror failed for '{path}': {e}")


# ---------------------------------------------------------------------------
# 1. Hierarchical Memory Node Operations
# ---------------------------------------------------------------------------

@tool
def memory_tree_store(
    path: str,
    title: str,
    content: str,
    category: str = "general",
    tags: str = "memory, general",
    importance: int = 5
) -> dict:
    """
    Stores or updates a structured memory node in the hierarchical Memory Tree.

    Args:
        path: Path in tree notation e.g. '/projects/stlc_tunisia/sponsors' or '/people/merouane_debbah'.
        title: Human-readable title of the memory node.
        content: Detailed knowledge, facts, or decision notes.
        category: Branch category ('personal', 'projects', 'pcb_hardware', 'research', 'people', 'preferences').
        tags: Comma-separated tags e.g. 'telecom, 6g, ieee'.
        importance: 1-10 priority scale (default 5).

    Returns:
        dict with status, memory id, path, and sync confirmation.
    """
    now = datetime.datetime.now().isoformat()
    conn = _get_db()
    with conn:
        conn.execute("""
            INSERT INTO memory_nodes (path, title, content, category, tags, importance, access_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                title=excluded.title,
                content=excluded.content,
                category=excluded.category,
                tags=excluded.tags,
                importance=excluded.importance,
                access_count=memory_nodes.access_count + 1,
                updated_at=excluded.updated_at
        """, (path, title, content, category, tags, importance, now, now))

    _sync_node_to_obsidian(path, title, category, content, tags)
    logger.info(f"[MemoryTree] Stored node: '{path}' (importance: {importance})")

    return {
        "status": "success",
        "summary": f"Memory node '{path}' stored successfully in Memory Tree and mirrored to Obsidian Vault.",
        "data": {"path": path, "title": title, "category": category, "importance": importance}
    }


@tool
def memory_tree_query(
    query: str = "",
    category: str = "",
    min_importance: int = 1,
    limit: int = 10
) -> dict:
    """
    Searches the hierarchical Memory Tree for relevant facts, decisions, and knowledge.

    Args:
        query: Keywords to search across title, content, path, or tags.
        category: Optional category filter e.g. 'projects', 'people', 'pcb_hardware'.
        min_importance: Minimum importance threshold (1-10).
        limit: Maximum results to return (default: 10).

    Returns:
        dict with status, matched nodes list, and tree hierarchy.
    """
    conn = _get_db()
    sql = "SELECT id, path, title, content, category, tags, importance, access_count, updated_at FROM memory_nodes WHERE importance >= ?"
    params: List[Any] = [min_importance]

    if category:
        sql += " AND category = ?"
        params.append(category)

    if query:
        sql += " AND (title LIKE ? OR content LIKE ? OR path LIKE ? OR tags LIKE ?)"
        pattern = f"%{query}%"
        params.extend([pattern, pattern, pattern, pattern])

    sql += " ORDER BY importance DESC, access_count DESC, updated_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "path": r["path"],
            "title": r["title"],
            "category": r["category"],
            "tags": r["tags"],
            "importance": r["importance"],
            "access_count": r["access_count"],
            "updated_at": r["updated_at"],
            "content": r["content"][:300] + ("..." if len(r["content"]) > 300 else "")
        })

    return {
        "status": "success",
        "summary": f"Found {len(results)} memory nodes matching query '{query}'.",
        "data": {"count": len(results), "nodes": results}
    }


# ---------------------------------------------------------------------------
# 2. Goals & Todos Kanban Operations
# ---------------------------------------------------------------------------

@tool
def goals_kanban_upsert(
    title: str,
    description: str = "",
    status: str = "todo",
    priority: str = "medium",
    category: str = "general",
    deadline: str = "",
    progress: int = 0,
    goal_id: Optional[int] = None
) -> dict:
    """
    Creates or updates a goal/task in the Jarvis Goals Kanban board.

    Args:
        title: Goal or task title.
        description: Detailed requirements, subtasks, or checklist.
        status: Kanban status ('todo', 'in_progress', 'done', 'blocked').
        priority: Priority level ('low', 'medium', 'high', 'urgent').
        category: Area ('engineering', 'ieee_stlc', 'pcb', 'research', 'personal').
        deadline: ISO format date or human deadline e.g. '2026-10-15'.
        progress: Percentage progress 0-100.
        goal_id: Optional ID if updating an existing goal.

    Returns:
        dict with status, goal details, and updated kanban card.
    """
    now = datetime.datetime.now().isoformat()
    conn = _get_db()
    with conn:
        if goal_id:
            conn.execute("""
                UPDATE goals SET
                    title = ?, description = ?, status = ?, priority = ?,
                    category = ?, deadline = ?, progress = ?, updated_at = ?
                WHERE id = ?
            """, (title, description, status, priority, category, deadline, progress, now, goal_id))
            target_id = goal_id
        else:
            cur = conn.execute("""
                INSERT INTO goals (title, description, status, priority, category, deadline, progress, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, description, status, priority, category, deadline, progress, now, now))
            target_id = cur.lastrowid

    logger.info(f"[GoalsKanban] Goal #{target_id} '{title}' -> status: {status}, priority: {priority}")
    return {
        "status": "success",
        "summary": f"Goal #{target_id} '{title}' saved with status [{status.upper()}].",
        "data": {
            "id": target_id,
            "title": title,
            "status": status,
            "priority": priority,
            "progress": progress,
            "deadline": deadline
        }
    }


@tool
def goals_kanban_list(
    status: str = "",
    category: str = "",
    priority: str = ""
) -> dict:
    """
    Lists goals and tasks from the Jarvis Kanban board organized by column.

    Args:
        status: Optional filter ('todo', 'in_progress', 'done', 'blocked').
        category: Optional category filter e.g. 'ieee_stlc', 'pcb', 'engineering'.
        priority: Optional priority filter ('urgent', 'high', 'medium', 'low').

    Returns:
        dict with kanban columns (todo, in_progress, done, blocked) and total counts.
    """
    conn = _get_db()
    sql = "SELECT * FROM goals WHERE 1=1"
    params: List[Any] = []

    if status:
        sql += " AND status = ?"
        params.append(status)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if priority:
        sql += " AND priority = ?"
        params.append(priority)

    sql += " ORDER BY CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, updated_at DESC"
    rows = conn.execute(sql, params).fetchall()

    board: Dict[str, List[dict]] = {"todo": [], "in_progress": [], "done": [], "blocked": []}
    for r in rows:
        item = {
            "id": r["id"],
            "title": r["title"],
            "description": r["description"],
            "status": r["status"],
            "priority": r["priority"],
            "category": r["category"],
            "deadline": r["deadline"],
            "progress": r["progress"],
            "updated_at": r["updated_at"]
        }
        if r["status"] in board:
            board[r["status"]].append(item)

    return {
        "status": "success",
        "summary": f"Retrieved {len(rows)} goals across Kanban columns (Todo: {len(board['todo'])}, In Progress: {len(board['in_progress'])}, Done: {len(board['done'])}, Blocked: {len(board['blocked'])}).",
        "data": {
            "total": len(rows),
            "columns": board
        }
    }


# ---------------------------------------------------------------------------
# 3. People & Preferences Profile Memory
# ---------------------------------------------------------------------------

@tool
def people_profile_upsert(
    name: str,
    role_affiliation: str = "",
    email: str = "",
    phone: str = "",
    notes: str = "",
    tags: str = ""
) -> dict:
    """
    Saves or updates a contact or collaborator dossier in Jarvis People Memory.

    Args:
        name: Full name of the person/contact.
        role_affiliation: Title, company, or university.
        email: Email address.
        phone: Phone number.
        notes: Biographical notes, mutual history, communication style, or preferences.
        tags: Categorization tags e.g. 'keynote_speaker, ieee_fellow, sponsor_lead'.

    Returns:
        dict with status and profile summary.
    """
    now = datetime.datetime.now().isoformat()
    conn = _get_db()
    with conn:
        conn.execute("""
            INSERT INTO people_profiles (name, role_affiliation, email, phone, notes, tags, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                role_affiliation=excluded.role_affiliation,
                email=excluded.email,
                phone=excluded.phone,
                notes=excluded.notes,
                tags=excluded.tags,
                updated_at=excluded.updated_at
        """, (name, role_affiliation, email, phone, notes, tags, now))

    # Also store in memory tree under /people/{clean_name}
    clean_slug = name.lower().replace(" ", "_").replace(".", "")
    memory_tree_store.invoke({
        "path": f"/people/{clean_slug}",
        "title": f"Profile: {name}",
        "content": f"**Affiliation**: {role_affiliation}\n**Email**: {email}\n**Phone**: {phone}\n**Notes**: {notes}",
        "category": "people",
        "tags": tags or "people, contact",
        "importance": 7
    })

    return {
        "status": "success",
        "summary": f"Person profile for '{name}' recorded successfully.",
        "data": {"name": name, "role_affiliation": role_affiliation, "email": email}
    }
