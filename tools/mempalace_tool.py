"""
🏰 MemPalace Long-Term Verbatim Memory Tool for Jarvis.

Integrates MemPalace (https://github.com/mempalace/mempalace):
1. Verbatim long-term memory storage across sessions (no LLM summarization loss).
2. Spatial memory hierarchy (Wings -> Rooms -> Halls -> Drawers).
3. Hybrid semantic vector (local ONNX all-MiniLM-L6-v2) + BM25 keyword search.
4. L0 + L1 Wake-Up context for instant project re-orientation.
5. Temporal entity knowledge graph.
"""

import os
import sys
import json
import logging
import subprocess
from typing import Dict, Any, Optional, List
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

DEFAULT_PALACE_DIR = os.path.join(os.getcwd(), "scratch", "jarvis_palace")


def _run_mempalace_cli(args: List[str]) -> subprocess.CompletedProcess:
    """Executes mempalace CLI command with default palace path."""
    venv_python = sys.executable
    cmd = [venv_python, "-m", "mempalace.cli", "--palace", DEFAULT_PALACE_DIR] + args
    return subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())


@tool
def remember_decision_or_fact(
    content: str,
    room: str = "general",
    hall: str = "decisions",
    wing: str = "jarvis_pcb"
) -> dict:
    """
    Stores an exact verbatim memory entry (decision, hardware rule, user preference, bug fix) in MemPalace.
    Preserves exact code snippets, pinouts, and formulas without lossy summarization.

    Args:
        content: The verbatim text, formula, or architectural decision to store.
        room: Topic/subsystem room (e.g. 'thermal_design', 'kicad_ast', 'discord_bot', 'supply_chain').
        hall: Memory type (e.g. 'decisions', 'rules', 'bug_fixes', 'preferences').
        wing: Project workspace wing (default: 'jarvis_pcb').

    Returns:
        dict with status and confirmation of stored memory.
    """
    logger.info(f"[MemPalace] Storing memory in [{wing}/{room}/{hall}]: '{content[:60]}...'")
    
    # Write to a temporary file and mine it to preserve exact verbatim layout
    os.makedirs(os.path.join(DEFAULT_PALACE_DIR, "inbox"), exist_ok=True)
    temp_entry_file = os.path.join(DEFAULT_PALACE_DIR, "inbox", f"entry_{abs(hash(content))}.md")
    
    with open(temp_entry_file, "w", encoding="utf-8") as f:
        f.write(f"# {room.upper()} — {hall.upper()}\n\n{content}\n")
    
    res = _run_mempalace_cli(["mine", temp_entry_file, "--wing", wing])
    
    return {
        "status": "success" if res.returncode == 0 else "error",
        "summary": f"Memory stored in MemPalace [{wing}/{room}/{hall}].",
        "data": {
            "wing": wing,
            "room": room,
            "hall": hall,
            "content_preview": content[:120],
            "output": res.stdout.strip()
        }
    }


@tool
def recall_verbatim_memory(
    query: str,
    room: str = "",
    wing: str = "jarvis_pcb"
) -> dict:
    """
    Searches MemPalace long-term memory for exact verbatim discussions, formulas, rules, and past decisions.
    Uses hybrid cosine vector similarity + BM25 keyword matching on local CPU.

    Args:
        query: Search term or question (e.g. 'IPC-2221 temperature rise formula', 'buck converter MP1584 frequency').
        room: Optional room filter (e.g. 'thermal_design', 'discord_bot').
        wing: Project workspace wing (default: 'jarvis_pcb').

    Returns:
        dict with matching drawers, cosine similarity scores, source files, and excerpts.
    """
    logger.info(f"[MemPalace] Searching memory for query: '{query}' (wing={wing}, room={room})")
    
    args = ["search", query, "--wing", wing]
    if room:
        args.extend(["--room", room])
        
    res = _run_mempalace_cli(args)
    stdout = res.stdout.strip()
    
    return {
        "status": "success" if res.returncode == 0 else "error",
        "summary": f"MemPalace search for '{query}' completed.",
        "data": {
            "query": query,
            "results_text": stdout if stdout else "No exact matches found."
        }
    }


@tool
def get_mempalace_wake_up(
    wing: str = "jarvis_pcb"
) -> dict:
    """
    Retrieves compressed L0 identity and L1 essential story context (~600-900 tokens) for instant project orientation.

    Args:
        wing: Project workspace wing (default: 'jarvis_pcb').

    Returns:
        dict containing wake-up briefing text and token count.
    """
    logger.info(f"[MemPalace] Generating wake-up context for wing: '{wing}'")
    res = _run_mempalace_cli(["wake-up", "--wing", wing])
    
    return {
        "status": "success" if res.returncode == 0 else "error",
        "summary": f"MemPalace wake-up briefing generated for '{wing}'.",
        "data": {
            "wake_up_text": res.stdout.strip()
        }
    }


@tool
def mine_codebase_to_palace(
    target_dir: str = ".",
    wing: str = "jarvis_pcb"
) -> dict:
    """
    Mines all files in a codebase, documentation folder, or conversation logs into MemPalace.

    Args:
        target_dir: Directory path to scan and index (default: current workspace).
        wing: Project workspace wing (default: 'jarvis_pcb').

    Returns:
        dict with total files processed and drawers filed.
    """
    abs_target = os.path.abspath(target_dir)
    logger.info(f"[MemPalace] Mining directory '{abs_target}' into wing '{wing}'")
    
    res = _run_mempalace_cli(["mine", abs_target, "--wing", wing])
    
    return {
        "status": "success" if res.returncode == 0 else "error",
        "summary": f"MemPalace mining completed for '{abs_target}'.",
        "data": {
            "target": abs_target,
            "output": res.stdout.strip()
        }
    }
