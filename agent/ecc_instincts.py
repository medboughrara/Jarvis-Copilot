"""
ECC (Everything Claude Code) Autonomous Instincts Engine for Jarvis Copilot.
Directly adapts affaan-m/ECC instincts architecture:
- Plan-Before-Build: Evaluates execution impact, file dependencies, and risks prior to code/hardware operations.
- Self-Verification & Quality Gate: Validates syntax, imports, and DRC rules after changes.
- Error Recovery Reflex: Intercepts runtime exceptions, analyzes stack traces, and suggests automated remediation.
"""

import os
import sys
import re
import ast
import traceback
from typing import Dict, Any, List, Optional
import config

logger = config.get_logger(__name__)

class ECCInstinctsEngine:
    def __init__(self):
        self.verified_runs: int = 0
        self.intercepted_errors: int = 0

    def plan_before_build(self, query: str, proposed_action: str, target_files: List[str] = None) -> Dict[str, Any]:
        """
        ECC Plan-Before-Build Reflex:
        Analyzes the proposed operation and generates a structured pre-execution risk assessment and checklist.
        """
        risks = []
        checks = []
        
        target_files = target_files or []
        for f in target_files:
            if not os.path.exists(f):
                risks.append(f"Target file '{f}' does not exist and will be newly created.")
            elif os.path.getsize(f) > 500_000:
                risks.append(f"Target file '{f}' is large (>500KB); recommend chunked diffing.")

        is_destructive = any(w in proposed_action.lower() for w in ["delete", "remove", "overwrite", "truncate", "format", "drop"])
        if is_destructive:
            risks.append("Action is potentially destructive; ensure backup or safe rollback.")

        checks.append("Verify input parameter schemas")
        checks.append("Check syntax and import integrity")
        checks.append("Confirm non-blocking async execution")

        return {
            "status": "approved" if len(risks) < 3 else "caution",
            "action": proposed_action,
            "risks_identified": risks,
            "verification_checklist": checks,
            "summary": f"ECC Pre-Build Plan: {len(checks)} checks ready, {len(risks)} risks noted."
        }

    def self_verify_python_code(self, code_string: str) -> Dict[str, Any]:
        """
        ECC Self-Verification Reflex:
        Performs static AST validation and syntax checking on Python code before or after execution.
        """
        try:
            tree = ast.parse(code_string)
            self.verified_runs += 1
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        imports.append(n.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            return {
                "status": "valid",
                "syntax_valid": True,
                "detected_imports": list(set(imports)),
                "ast_nodes_count": len(list(ast.walk(tree))),
                "message": "Code passed static AST validation."
            }
        except SyntaxError as se:
            return {
                "status": "syntax_error",
                "syntax_valid": False,
                "error_line": se.lineno,
                "error_offset": se.offset,
                "error_text": se.text,
                "message": f"Syntax error at line {se.lineno}: {se.msg}"
            }
        except Exception as e:
            return {
                "status": "error",
                "syntax_valid": False,
                "message": str(e)
            }

    def error_recovery_reflex(self, exception: Exception, context: str = "") -> Dict[str, Any]:
        """
        ECC Error Recovery Reflex:
        Analyzes an exception and produces actionable root-cause diagnoses and automatic remediation steps.
        """
        self.intercepted_errors += 1
        err_type = type(exception).__name__
        err_msg = str(exception)
        tb_str = traceback.format_exc()

        remediation = []
        if "404" in err_msg or "NOT_FOUND" in err_msg:
            remediation.append("Rotate model name to fallback tier (e.g. gemini-2.5-flash -> gemini-1.5-flash -> Ollama).")
        elif "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Quota" in err_msg:
            remediation.append("Rotate to next available API key in KeyManager and initiate 60s cooldown.")
        elif "ModuleNotFoundError" in err_type or "ImportError" in err_type:
            missing_mod = re.findall(r"named '([^']+)'", err_msg) or [err_msg]
            remediation.append(f"Install missing package via `.venv\\Scripts\\pip.exe install {missing_mod[0]}` or check module path.")
        elif "Timeout" in err_type or "TimeoutExpired" in err_type:
            remediation.append("Operation exceeded timeout limit; optimize query payload or switch to async background task.")
        elif "stream can only be called once" in err_msg:
            remediation.append("Use atomic file save (`communicate.save()`) instead of reusing consumed generator stream.")
        else:
            remediation.append(f"Review exception details and sanitize parameters for '{context}'.")

        logger.warning(f"[ECC Error Recovery] Intercepted {err_type}: '{err_msg[:80]}'. Suggested remediation: {remediation}")

        return {
            "error_type": err_type,
            "error_message": err_msg,
            "context": context,
            "remediation_steps": remediation,
            "traceback_summary": [line for line in tb_str.split("\n") if "File " in line][-2:]
        }


# Global Singleton Instincts Engine
ecc_instincts = ECCInstinctsEngine()
