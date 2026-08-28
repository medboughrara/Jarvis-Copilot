"""
ECC (Everything Claude Code) Tools for Jarvis Copilot.
Directly exposes ECC instincts and unified memory as LangChain tools:
- ecc_plan_action: Pre-execution risk assessment and verification checklist
- ecc_verify_python: Static AST syntax and import validation
- unified_memory_store: Scoped memory storage (user, project, session)
- unified_memory_query: Scoped memory retrieval
"""

import json
from typing import Dict, Any, List
from langchain_core.tools import tool
from agent.ecc_instincts import ecc_instincts
from agent.unified_memory import unified_memory
import config

logger = config.get_logger(__name__)

@tool
def ecc_plan_action(action_description: str, target_files: str = "[]") -> Dict[str, Any]:
    """
    ECC Plan-Before-Build tool: Generates a pre-execution safety and validation checklist before making code, EDA, or file modifications.
    
    Args:
        action_description: Description of the operation or code change to be performed.
        target_files: JSON array of file paths impacted by the action.
    """
    try:
        files_list = json.loads(target_files) if isinstance(target_files, str) and target_files.startswith("[") else []
    except Exception:
        files_list = []

    return ecc_instincts.plan_before_build(
        query=action_description,
        proposed_action=action_description,
        target_files=files_list
    )


@tool
def ecc_verify_python(code_snippet: str) -> Dict[str, Any]:
    """
    ECC Self-Verification tool: Validates Python syntax and imports using AST static analysis.
    
    Args:
        code_snippet: Python code to verify.
    """
    return ecc_instincts.self_verify_python_code(code_snippet)


@tool
def unified_memory_store(scope: str, key: str, value: str, metadata: str = "{}") -> Dict[str, Any]:
    """
    ECC Unified Memory storage across 'user', 'project', or 'session' scopes.
    
    Args:
        scope: 'user' (operator preferences), 'project' (repo architecture & deliverables), or 'session' (current chat context).
        key: The memory identifier key.
        value: The memory text or JSON string to store.
        metadata: Optional metadata JSON string.
    """
    try:
        meta_dict = json.loads(metadata) if isinstance(metadata, str) and metadata.startswith("{") else {}
    except Exception:
        meta_dict = {}

    unified_memory.set(scope=scope, key=key, value=value, metadata=meta_dict)
    return {
        "status": "success",
        "summary": f"Stored memory under scope [{scope.upper()}]: '{key}'",
        "data": {"scope": scope, "key": key}
    }


@tool
def unified_memory_query(scope: str, key: str = "") -> Dict[str, Any]:
    """
    ECC Unified Memory retrieval for 'user', 'project', or 'session' scopes.
    
    Args:
        scope: 'user', 'project', or 'session'.
        key: Specific key to look up (if empty, returns all items in the scope).
    """
    if key:
        val = unified_memory.get(scope=scope, key=key)
        return {
            "status": "success",
            "summary": f"Retrieved memory [{scope.upper()} -> {key}]",
            "data": {"key": key, "value": val}
        }
    else:
        items = unified_memory.list_scope(scope=scope)
        return {
            "status": "success",
            "summary": f"Retrieved {len(items)} memories from scope [{scope.upper()}]",
            "data": {"scope": scope, "items": items}
        }
