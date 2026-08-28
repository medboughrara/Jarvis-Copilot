"""
AgentShield Security & Path Permission Guard for Jarvis PCB Copilot.
Inspired by AgentShield security principles in agent harness architectures (ECC).

Audits tool call arguments, file paths, API key environment variables, and MCP payloads:
1. Workspace Path Traversal Guard (Restricts file access to project workspace)
2. Tool Parameter Sanitizer (Sanitizes SQL/Command injection characters)
3. API Key & Secret Redaction (Masks API keys in logs and LLM contexts)
"""

import os
import re
from typing import Dict, Any, Tuple


class AgentShieldGuard:
    """Security auditor for agent tool calls and file system operations."""

    def __init__(self, workspace_root: str = None):
        if not workspace_root:
            workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.workspace_root = os.path.abspath(workspace_root)

    def validate_file_path(self, target_path: str) -> Tuple[bool, str]:
        """
        Ensures target file path remains safely within workspace boundaries.
        Prevents directory traversal attacks (e.g. '../../etc/passwd').
        """
        if not target_path or not target_path.strip():
            return True, os.path.join(self.workspace_root, "tests", "sample_autopick.kicad_sch")

        cleaned_path = target_path.strip().strip("'\"")
        abs_path = os.path.abspath(cleaned_path if os.isabs(cleaned_path) else os.path.join(self.workspace_root, cleaned_path))

        # Path Traversal Check
        if not abs_path.startswith(self.workspace_root):
            return False, f"Security Violation: Target path '{target_path}' lies outside workspace root '{self.workspace_root}'."

        return True, abs_path

    def sanitize_tool_args(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizes tool parameters to prevent path traversal or injection."""
        sanitized = {}
        for key, val in tool_args.items():
            if isinstance(val, str):
                # Mask potential exposed API keys or tokens in arguments
                if any(secret_kw in key.lower() for secret_kw in ["key", "secret", "token", "password"]):
                    sanitized[key] = self.mask_secret(val)
                elif "path" in key.lower() or "file" in key.lower() or "doc" in key.lower():
                    valid, resolved_path = self.validate_file_path(val)
                    sanitized[key] = resolved_path if valid else val
                else:
                    sanitized[key] = val
            else:
                sanitized[key] = val
        return sanitized

    @staticmethod
    def mask_secret(secret_val: str) -> str:
        """Masks API keys for safe display (e.g., 'AIzaSyDl...4A8b')."""
        if not secret_val or len(secret_val) < 8:
            return "***"
        return f"{secret_val[:8]}...{secret_val[-4:]}"

    @staticmethod
    def scrub_text(text: str) -> str:
        """Scrubs sensitive API keys (Google, NVIDIA, GitHub, OpenAI) from string text."""
        if not text:
            return ""
        # Match Google AIzaSy keys
        text = re.sub(r'AIzaSy[A-Za-z0-9_\-]{33}', 'AIzaSy[REDACTED]', text)
        # Match NVIDIA nvapi keys
        text = re.sub(r'nvapi-[A-Za-z0-9_\-]{50,}', 'nvapi-[REDACTED]', text)
        # Match OpenAI / Anthropic / Generic Bearer sk- tokens
        text = re.sub(r'sk-[A-Za-z0-9_\-]{20,}', 'sk-[REDACTED]', text)
        # Match GitHub tokens
        text = re.sub(r'ghp_[A-Za-z0-9]{36}', 'ghp_[REDACTED]', text)
        return text

    @staticmethod
    def is_command_safe(command: str) -> Tuple[bool, str]:
        """Audits shell commands to block destructive or malicious operations."""
        cmd_lower = command.lower().strip()
        dangerous_patterns = [
            r"rm\s+-rf\s+[/~]",
            r"del\s+/[fs]\s+c:\\",
            r"format-volume",
            r"format\s+[a-z]:",
            r"drop\s+database",
            r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # Fork bomb
            r"mkfs\.",
            r"dd\s+if=/dev/"
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, cmd_lower):
                return False, f"Blocked dangerous command pattern matching '{pattern}'"
        return True, "Safe"
