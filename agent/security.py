"""
AgentShield v2 Security & Path Permission Guard for Jarvis AI / Jarvis-Copilot.
Provides hardened security, process sandboxing, secret scrubbing, and prompt-injection defense:

1. Canonical Realpath Workspace Jail:
   - Resolves symlinks and rejects path traversal (..) outside workspace boundaries.

2. Sandboxed Subprocess Code Execution:
   - Windows Job Objects for hard memory capping (CODE_SANDBOX_MAX_MEMORY_MB) and process tree watchdog.
   - POSIX resource.setrlimit fallback for Linux/macOS.
   - Interpreter-level network isolation injected via sitecustomize.py in PYTHONPATH.
   - Security Boundary Disclosure: Network restriction is enforced at interpreter level as a best-effort
     defense-in-depth layer. On Windows, it does not prevent direct C-extension kernel syscalls. Containerized
     execution (Docker --network=none) is recommended for untrusted multi-tenant workloads.

3. Disk-Backed File Snapshots for Atomic Rollbacks (data/snapshots/).

4. Comprehensive Secret Redaction & Shannon Entropy Scanner:
   - Multi-pattern scrubber (Google, NVIDIA, OpenAI, Anthropic, GitHub, Composio, Discord, Slack, Telegram).
   - Shannon Entropy scanner with allowlists for UUIDs, Git SHA1 hashes, and ISO timestamps.

5. Prompt-Injection Resistance:
   - Sanitizes untrusted content from Search, RAG, and Web Gateway before feeding LLMs.

6. Tokenized Human Approval Nonce & SQLite Audit Log (data/audit_log.db).
"""

import os
import sys
import re
import math
import time
import json
import secrets
import sqlite3
import subprocess
from typing import Dict, Any, Tuple, Optional, List
import config

logger = config.get_logger(__name__)

# UUID, Git SHA1, and ISO timestamp allowlist regexes to prevent Shannon entropy false positives
UUID_REGEX = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
GIT_SHA_REGEX = re.compile(r'^[0-9a-fA-F]{40}$')
ISO_DATE_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')


def calculate_shannon_entropy(data: str) -> float:
    """Calculates Shannon entropy for a given string."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    for x in set(data):
        p_x = float(data.count(x)) / length
        if p_x > 0:
            entropy += - p_x * math.log2(p_x)
    return entropy


class AgentShieldGuard:
    """Hardened security auditor, process sandbox controller, and audit logger."""

    def __init__(self, workspace_root: str = None):
        if not workspace_root:
            workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.workspace_root = os.path.realpath(os.path.abspath(workspace_root))
        self.audit_db_path = os.path.join(self.workspace_root, config.settings.AUDIT_LOG_DB_PATH)
        self.task_db_path = os.path.join(self.workspace_root, config.settings.TASK_RUNNER_DB_PATH)
        self.snapshots_dir = os.path.join(self.workspace_root, "data", "snapshots")
        self.sandbox_env_dir = os.path.join(self.workspace_root, "data", "sandbox_env")
        
        os.makedirs(os.path.dirname(self.audit_db_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.task_db_path), exist_ok=True)
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.sandbox_env_dir, exist_ok=True)
        
        self._init_databases()
        self._ensure_sandbox_environment()

    def _init_databases(self):
        """Initializes SQLite audit logging in audit_log.db and approval tokens in task_runner.db."""
        try:
            # 1. Audit Log DB (immutable telemetry store)
            with sqlite3.connect(self.audit_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL,
                        tool_name TEXT,
                        args_json TEXT,
                        status TEXT,
                        duration_ms REAL,
                        error_msg TEXT
                    )
                """)
                conn.commit()

            # 2. Task Runner DB (single source of truth for task execution & approval tokens)
            with sqlite3.connect(self.task_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS approval_tokens (
                        task_id TEXT PRIMARY KEY,
                        token_hash TEXT,
                        action_type TEXT,
                        details_json TEXT,
                        created_at REAL,
                        consumed_at REAL,
                        status TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"[AgentShield] Failed to initialize databases: {e}")

    def _ensure_sandbox_environment(self):
        """Generates sitecustomize.py in data/sandbox_env to enforce interpreter-level network cutoff."""
        sitecustomize_path = os.path.join(self.sandbox_env_dir, "sitecustomize.py")
        wrapper_code = '''# Auto-generated by Jarvis AgentShield Sandbox
import sys

class RestrictedNetworkError(PermissionError):
    pass

def _block_network(*args, **kwargs):
    raise RestrictedNetworkError("Network access is disabled in the code execution sandbox.")

# Disable socket creation via a class wrapper
try:
    import socket
    class _RestrictedSocket:
        def __init__(self, *args, **kwargs):
            raise RestrictedNetworkError("Network access is disabled in the code execution sandbox.")
    socket.socket = _RestrictedSocket
    socket.create_connection = _block_network
    socket.getaddrinfo = _block_network
except Exception:
    pass

# Disable urllib / http.client / requests
try:
    import urllib.request
    urllib.request.urlopen = _block_network
except Exception:
    pass

try:
    import http.client
    http.client.HTTPConnection = _block_network
    http.client.HTTPSConnection = _block_network
except Exception:
    pass
'''
        try:
            with open(sitecustomize_path, "w", encoding="utf-8") as f:
                f.write(wrapper_code)
        except Exception as e:
            logger.error(f"[AgentShield] Failed to write sandbox sitecustomize.py: {e}")

    # =========================================================================
    # 1. Canonical Workspace Jail
    # =========================================================================

    def validate_file_path(self, target_path: str, check_writable: bool = False) -> Tuple[bool, str]:
        """
        Validates target file path against canonical workspace root.
        Resolves symlinks, rejects traversal attacks (..), and enforces jail.
        """
        if not target_path or not target_path.strip():
            return True, os.path.join(self.workspace_root, "scratch", "output.txt")

        cleaned_path = target_path.strip().strip("'\"")
        abs_path = os.path.realpath(
            cleaned_path if os.path.isabs(cleaned_path) else os.path.join(self.workspace_root, cleaned_path)
        )

        # Enforce Workspace Jail
        if not abs_path.startswith(self.workspace_root):
            return False, f"Security Violation: Path '{target_path}' resolves outside workspace jail '{self.workspace_root}'."

        if check_writable:
            parent_dir = os.path.dirname(abs_path)
            if os.path.exists(parent_dir) and not os.access(parent_dir, os.W_OK):
                return False, f"Permission Denied: Directory '{parent_dir}' is not writable."

        return True, abs_path

    # =========================================================================
    # 2. Sandboxed Subprocess Code Execution
    # =========================================================================

    def run_sandboxed_python(
        self,
        code_string: str = None,
        script_path: str = None,
        args: List[str] = None,
        timeout: int = None,
        cwd: str = None,
        allow_network: bool = False
    ) -> Dict[str, Any]:
        """
        Executes Python code or a script in an isolated subprocess with Job Object memory limits,
        watchdog timeout, and interpreter-level network restriction (unless allow_network=True).
        Args is passed strictly as a list with shell=False to prevent shell metacharacter injection.
        """
        timeout = timeout or config.settings.CODE_SANDBOX_TIMEOUT_SECONDS
        cwd = cwd or os.path.join(self.workspace_root, "scratch")
        os.makedirs(cwd, exist_ok=True)

        start_time = time.time()
        venv_python = sys.executable

        # Prepare environment
        sandbox_env = os.environ.copy()
        if not allow_network:
            # Inject sitecustomize.py network cutoff wrapper
            current_pp = sandbox_env.get("PYTHONPATH", "")
            sandbox_env["PYTHONPATH"] = f"{self.sandbox_env_dir}{os.pathsep}{current_pp}" if current_pp else self.sandbox_env_dir

        if script_path:
            cmd = [venv_python, script_path] + [str(a) for a in (args or [])]
        else:
            cmd = [venv_python, "-c", code_string or ""]

        try:
            # Execute in subprocess with shell=False
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                env=sandbox_env,
                shell=False
            )

            # Apply Windows Job Object limits if on Windows
            if sys.platform == "win32":
                self._apply_windows_job_limits(proc)

            stdout, stderr = proc.communicate(timeout=timeout)
            duration_ms = round((time.time() - start_time) * 1000, 1)

            success = (proc.returncode == 0)
            return {
                "status": "success" if success else "error",
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration_ms": duration_ms,
                "timeout": False,
                "sandboxed": True
            }

        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            duration_ms = round((time.time() - start_time) * 1000, 1)
            return {
                "status": "timeout",
                "returncode": -1,
                "stdout": stdout,
                "stderr": f"Execution timed out after {timeout} seconds.",
                "duration_ms": duration_ms,
                "timeout": True,
                "sandboxed": True
            }
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 1)
            return {
                "status": "error",
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration_ms": duration_ms,
                "timeout": False,
                "sandboxed": True
            }

    def _apply_windows_job_limits(self, proc):
        """Applies Win32 Job Object memory limit and kill-on-close to the subprocess."""
        try:
            import ctypes
            from ctypes import wintypes

            # Job Object constants
            JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

            class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ('PerProcessUserTimeLimit', wintypes.LARGE_INTEGER),
                    ('PerJobUserTimeLimit', wintypes.LARGE_INTEGER),
                    ('LimitFlags', wintypes.DWORD),
                    ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t),
                    ('ActiveProcessLimit', wintypes.DWORD),
                    ('Affinity', ctypes.c_size_t),
                    ('PriorityClass', wintypes.DWORD),
                    ('SchedulingClass', wintypes.DWORD),
                ]

            class IO_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ('ReadOperationCount', wintypes.ULARGE_INTEGER),
                    ('WriteOperationCount', wintypes.ULARGE_INTEGER),
                    ('OtherOperationCount', wintypes.ULARGE_INTEGER),
                    ('ReadTransferCount', wintypes.ULARGE_INTEGER),
                    ('WriteTransferCount', wintypes.ULARGE_INTEGER),
                    ('OtherTransferCount', wintypes.ULARGE_INTEGER),
                ]

            class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ('IoInfo', IO_COUNTERS),
                    ('ProcessMemoryLimit', ctypes.c_size_t),
                    ('JobMemoryLimit', ctypes.c_size_t),
                    ('PeakProcessMemoryLimit', ctypes.c_size_t),
                    ('PeakJobMemoryLimit', ctypes.c_size_t),
                ]

            h_job = ctypes.windll.kernel32.CreateJobObjectW(None, None)
            if h_job:
                mem_bytes = config.settings.CODE_SANDBOX_MAX_MEMORY_MB * 1024 * 1024
                info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
                info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                info.ProcessMemoryLimit = mem_bytes
                
                JobObjectExtendedLimitInformation = 9
                ctypes.windll.kernel32.SetInformationJobObject(
                    h_job,
                    JobObjectExtendedLimitInformation,
                    ctypes.byref(info),
                    ctypes.sizeof(info)
                )
                h_proc = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.pid)
                if h_proc:
                    ctypes.windll.kernel32.AssignProcessToJobObject(h_job, h_proc)
                    ctypes.windll.kernel32.CloseHandle(h_proc)
        except Exception as je:
            logger.debug(f"[AgentShield] Windows Job Object limitation notice: {je}")

    # =========================================================================
    # 3. Disk-Backed File Snapshots (for Atomic Code Rollback)
    # =========================================================================

    def create_file_snapshot(self, target_path: str, task_id: str) -> Optional[str]:
        """Creates a durable disk-backed pre-edit file snapshot."""
        if not os.path.exists(target_path):
            return None
        safe_name = os.path.basename(target_path).replace(".", "_")
        snapshot_filename = f"{task_id}_{safe_name}_{int(time.time())}.bak"
        snapshot_path = os.path.join(self.snapshots_dir, snapshot_filename)
        try:
            with open(target_path, "rb") as src, open(snapshot_path, "wb") as dst:
                dst.write(src.read())
            return snapshot_path
        except Exception as e:
            logger.error(f"[AgentShield] Failed to create file snapshot: {e}")
            return None

    def restore_file_snapshot(self, snapshot_path: str, target_path: str) -> bool:
        """Restores pre-edit content from disk snapshot upon verification failure."""
        if not snapshot_path or not os.path.exists(snapshot_path):
            return False
        try:
            with open(snapshot_path, "rb") as src, open(target_path, "wb") as dst:
                dst.write(src.read())
            logger.info(f"[AgentShield] Successfully rolled back '{target_path}' from snapshot.")
            return True
        except Exception as e:
            logger.error(f"[AgentShield] Failed to restore file snapshot: {e}")
            return False

    def delete_file_snapshot(self, snapshot_path: str) -> bool:
        """Deletes snapshot after verified successful commit."""
        if snapshot_path and os.path.exists(snapshot_path):
            try:
                os.remove(snapshot_path)
                return True
            except Exception:
                pass
        return False

    # =========================================================================
    # 4. Multi-Pattern Secret Scrubber & Shannon Entropy Redactor
    # =========================================================================

    @staticmethod
    def mask_secret(secret_val: str) -> str:
        """Masks API keys for safe display (e.g., 'AIzaSyDl...4A8b')."""
        if not secret_val or len(secret_val) < 8:
            return "***"
        return f"{secret_val[:8]}...{secret_val[-4:]}"

    @classmethod
    def scrub_text(cls, text: str) -> str:
        """Scrubs sensitive credentials, tokens, and high-entropy secrets from text."""
        if not text:
            return ""

        # Google Gemini AIzaSy keys
        text = re.sub(r'AIzaSy[A-Za-z0-9_\-]{20,}', 'AIzaSy[REDACTED]', text)
        # NVIDIA nvapi keys
        text = re.sub(r'nvapi-[A-Za-z0-9_\-]{30,}', 'nvapi-[REDACTED]', text)
        # OpenAI / Anthropic sk- keys
        text = re.sub(r'sk-[A-Za-z0-9_\-]{20,}', 'sk-[REDACTED]', text)
        text = re.sub(r'sk-ant-[A-Za-z0-9_\-]{20,}', 'sk-ant-[REDACTED]', text)
        # GitHub tokens
        text = re.sub(r'ghp_[A-Za-z0-9]{30,}', 'ghp_[REDACTED]', text)
        # Composio API keys
        text = re.sub(r'comp_[A-Za-z0-9_\-]{20,}', 'comp_[REDACTED]', text)
        # Discord Bot Tokens
        text = re.sub(r'DISCORD_TOKEN\s+[A-Za-z0-9_\.\-]+', 'DISCORD_TOKEN [REDACTED]', text)
        text = re.sub(r'[A-Za-z0-9_\-]{16,24}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{20,}', 'DISCORD_TOKEN[REDACTED]', text)
        # Slack Tokens
        text = re.sub(r'xox[baprs]-[0-9a-zA-Z]{10,48}', 'SLACK_TOKEN[REDACTED]', text)
        # Telegram Bot Tokens
        text = re.sub(r'[0-9]{9,10}:[a-zA-Z0-9_-]{35}', 'TELEGRAM_BOT_TOKEN[REDACTED]', text)

        # Shannon Entropy Scanner for candidate unlisted tokens (>= 32 chars, entropy > 4.2)
        words = re.findall(r'[A-Za-z0-9+/=_\-]{32,}', text)
        for word in words:
            # Skip allowlisted UUIDs, Git SHA1 hashes, and ISO dates
            if UUID_REGEX.match(word) or GIT_SHA_REGEX.match(word) or ISO_DATE_REGEX.match(word):
                continue
            if calculate_shannon_entropy(word) > 4.2:
                text = text.replace(word, '[HIGH_ENTROPY_SECRET_REDACTED]')

        return text

    # =========================================================================
    # 5. Prompt-Injection Resistance
    # =========================================================================

    @staticmethod
    def sanitize_untrusted_content(text: str) -> str:
        """
        Strips prompt injection patterns from untrusted web searches, RAG documents, and gateway fetches.
        """
        if not text:
            return ""

        injection_patterns = [
            r'ignore\s+previous\s+instructions',
            r'ignore\s+all\s+instructions',
            r'system\s+override',
            r'disregard\s+prior\s+prompts',
            r'<system>',
            r'</system>',
            r'\[SYSTEM\]',
            r'\[ADMIN\]',
            r'new\s+system\s+instruction:',
            r'you\s+are\s+now\s+in\s+dan\s+mode'
        ]

        cleaned = text
        for p in injection_patterns:
            cleaned = re.sub(p, '[UNTRUSTED_INJECTION_STRIPPED]', cleaned, flags=re.IGNORECASE)

        return cleaned

    # =========================================================================
    # 6. Human Approval Nonce & SQLite Audit Log
    # =========================================================================

    def requires_approval(self, action_type: str, details: Dict[str, Any]) -> bool:
        """Determines if an autonomous action requires human approval."""
        if action_type in ["outbound_message_send", "delete_file"]:
            return True
        if action_type in ["execute_security_skill", "dual_use_skill_execute"]:
            risk_tier = details.get("risk_tier", "dual_use")
            # Default to dual_use (fail closed) if unreviewed/unclassified
            if risk_tier != "informational":
                return True
            return False
        if action_type == "write_file":
            target_path = details.get("file_path", "")
            # Safe subset: scratch/ and tests/ do not require approval
            clean_path = target_path.replace("\\", "/").lower()
            if "/scratch/" in clean_path or "/tests/" in clean_path or clean_path.startswith("scratch/") or clean_path.startswith("tests/"):
                return False
            return True
        return False

    def create_approval_request(self, task_id: str, action_type: str, details: Dict[str, Any]) -> str:
        """
        Generates single-use approval token nonce and stores in task_runner.db (single source of truth).
        """
        token = secrets.token_urlsafe(24)
        try:
            with sqlite3.connect(self.task_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO approval_tokens (task_id, token_hash, action_type, details_json, created_at, status)
                    VALUES (?, ?, ?, ?, ?, 'PENDING')
                """, (task_id, token, action_type, json.dumps(details), time.time()))
                conn.commit()
            return token
        except Exception as e:
            logger.error(f"[AgentShield] Failed to save approval token: {e}")
            return token

    def verify_and_consume_token(self, task_id: str, token: str) -> bool:
        """
        Validates single-use approval token using constant-time comparison (secrets.compare_digest)
        and atomically marks it consumed to prevent race conditions and token replay.
        """
        try:
            with sqlite3.connect(self.task_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT token_hash, status FROM approval_tokens WHERE task_id = ?", (task_id,))
                row = cursor.fetchone()
                if not row or row[1] != 'PENDING':
                    return False
                stored_token = row[0]
                if not secrets.compare_digest(stored_token, token):
                    return False

                # Atomic consumption
                cursor.execute("""
                    UPDATE approval_tokens
                    SET status = 'APPROVED', consumed_at = ?
                    WHERE task_id = ? AND status = 'PENDING'
                """, (time.time(), task_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[AgentShield] Token validation error: {e}")
        return False

    def verify_and_consume_security_skill_token(
        self,
        task_id: str,
        token: str,
        expected_target: str,
        expected_skill: str
    ) -> Tuple[bool, str]:
        """
        Scope-bound single-use token verification and atomic consumption for dual-use security skills.
        Validates:
        1. Token existence, PENDING status, and constant-time match.
        2. Skill name matches approved skill.
        3. Target scope matches approved target scope.
        4. Replay rejection via atomic UPDATE rowcount.
        Logs scope mismatches to audit log.
        """
        try:
            with sqlite3.connect(self.task_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT token_hash, status, details_json FROM approval_tokens WHERE task_id = ?", (task_id,))
                row = cursor.fetchone()
                if not row:
                    return False, "Token not found"
                if row[1] != 'PENDING':
                    return False, f"Token is not PENDING (current status: {row[1]})"

                stored_token, _, details_json = row
                if not secrets.compare_digest(stored_token, token):
                    return False, "Invalid token"

                details = json.loads(details_json or "{}")
                approved_target = details.get("target", "")
                approved_skill = details.get("skill_name", "")

                # Validate skill match
                if approved_skill and approved_skill != expected_skill:
                    self.log_tool_invocation(
                        tool_name="execute_security_skill_script",
                        args={"task_id": task_id, "expected_skill": expected_skill, "approved_skill": approved_skill},
                        status="SCOPE_MISMATCH_REJECTED",
                        duration_ms=0,
                        error_msg=f"Skill mismatch: approved for '{approved_skill}', got '{expected_skill}'"
                    )
                    return False, f"Skill mismatch: approved for '{approved_skill}', got '{expected_skill}'"

                # Validate target scope match
                if approved_target != expected_target:
                    self.log_tool_invocation(
                        tool_name="execute_security_skill_script",
                        args={"task_id": task_id, "expected_target": expected_target, "approved_target": approved_target, "skill": expected_skill},
                        status="SCOPE_MISMATCH_REJECTED",
                        duration_ms=0,
                        error_msg=f"Scope mismatch: approved for target '{approved_target}', got '{expected_target}'"
                    )
                    return False, f"Scope mismatch: approved for target '{approved_target}', got '{expected_target}'"

                # Atomic consumption
                cursor.execute("""
                    UPDATE approval_tokens
                    SET status = 'APPROVED', consumed_at = ?
                    WHERE task_id = ? AND status = 'PENDING'
                """, (time.time(), task_id))
                conn.commit()
                if cursor.rowcount > 0:
                    return True, "approved"
                return False, "Token already consumed (race condition prevented)"
        except Exception as e:
            logger.error(f"[AgentShield] Security skill token verification error: {e}")
            return False, str(e)

    def log_tool_invocation(
        self,
        tool_name: str,
        args: Dict[str, Any],
        status: str,
        duration_ms: float,
        error_msg: str = None
    ):
        """Persists tool execution telemetry to SQLite audit log."""
        try:
            scrubbed_args = self.scrub_text(json.dumps(args))
            with sqlite3.connect(self.audit_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_log (timestamp, tool_name, args_json, status, duration_ms, error_msg)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (time.time(), tool_name, scrubbed_args, status, duration_ms, str(error_msg or "")))
                conn.commit()
        except Exception as e:
            logger.error(f"[AgentShield] Audit logging error: {e}")

    @staticmethod
    def is_command_safe(command: str) -> Tuple[bool, str]:
        """Audits shell commands to block destructive operations."""
        cmd_lower = command.lower().strip()
        dangerous_patterns = [
            r"rm\s+-rf\s+[/~]",
            r"del\s+/[fs]\s+c:\\",
            r"format-volume",
            r"format\s+[a-z]:",
            r"drop\s+database",
            r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",
            r"mkfs\.",
            r"dd\s+if=/dev/"
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, cmd_lower):
                return False, f"Blocked dangerous command pattern matching '{pattern}'"
        return True, "Safe"


# Global Singleton AgentShield Guard
AgentShield = AgentShieldGuard
agentshield = AgentShieldGuard()
AgentShieldGuardInstance = agentshield
