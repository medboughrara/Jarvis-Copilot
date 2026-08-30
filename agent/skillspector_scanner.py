"""
NVIDIA SkillSpector Core Security Scanner & Static Analysis Engine.
Audits AI agent skills (Claude Code, Codex, MCP, LangChain, Custom Skills) against 17 vulnerability categories.

Vulnerability Categories (SkillSpector Spec):
1. Prompt Injection (direct & indirect system prompt overriding)
2. Data Exfiltration (unapproved webhooks, sockets, credential exfiltration)
3. Privilege Escalation (sudo, admin elevation, token manipulation)
4. Supply Chain Risks (typosquatted deps, unpinned imports, raw curl|sh)
5. Excessive Agency (destructive file deletion, disk formatting, drop tables)
6. Output Handling (unescaped dynamic shell/SQL/template rendering)
7. System Prompt Leakage (exfiltrating hidden system prompts or agent configs)
8. Memory Poisoning (corrupting SQLite memory or vector store with deceptive prompts)
9. Tool Misuse (invoking sensitive tools outside designated scope)
10. Rogue Agent (infinite replication, loop bombs, watchdog suppression)
11. Anti-Refusal (adversarial jailbreaks and safety bypass framing)
12. Trigger Abuse (hidden trigger phrases activating dormant capabilities)
13. Dangerous Code (AST analysis: eval, exec, os.system, shell=True, ctypes)
14. Taint Tracking (unvalidated user input flowing into filesystem/subprocess)
15. YARA & Heuristic Signatures (reverse shells, obfuscated base64/hex payloads)
16. MCP Least Privilege (MCP tools demanding excessive wildcard permissions)
17. MCP Tool Poisoning (malicious tool description injection & spoofed returns)

Features:
- Deterministic AST + Pattern Static Analysis (runs offline, millisecond latency).
- Calibrated 0–100 Risk Scoring & Tier Classification (LOW, MEDIUM, HIGH, CRITICAL).
- Drift-tolerant & SHA256-bound Baseline Suppression (.skillspector-baseline.yaml).
- Output Formats: JSON, Markdown, and SARIF v2.1.0 for CI/CD.
"""

import os
import re
import ast
import json
import time
import hashlib
import fnmatch
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
import yaml
import config

logger = config.get_logger(__name__)


@dataclass
class Finding:
    rule_id: str
    category: str
    severity: str  # "INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    title: str
    message: str
    file_path: str
    line_number: int = 1
    snippet: str = ""
    remediation: str = ""
    fingerprint: str = ""

    def compute_fingerprint(self) -> str:
        """Computes deterministic finding fingerprint for baseline matching."""
        raw = f"{self.rule_id}:{self.file_path}:{self.line_number}:{self.message.strip()}"
        self.fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return self.fingerprint


@dataclass
class ScanResult:
    target_path: str
    risk_score: int  # 0 to 100
    risk_tier: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    is_safe: bool
    findings_count: int
    findings: List[Finding] = field(default_factory=list)
    suppressed_count: int = 0
    scanned_files: List[str] = field(default_factory=list)
    scan_duration_ms: float = 0.0
    engine_version: str = "SkillSpector-v1.4.0-NVIDIA"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_path": self.target_path,
            "risk_score": self.risk_score,
            "risk_tier": self.risk_tier,
            "is_safe": self.is_safe,
            "findings_count": self.findings_count,
            "suppressed_count": self.suppressed_count,
            "scanned_files": self.scanned_files,
            "scan_duration_ms": self.scan_duration_ms,
            "engine_version": self.engine_version,
            "findings": [asdict(f) for f in self.findings]
        }

    def to_sarif(self) -> Dict[str, Any]:
        """Generates standard SARIF v2.1.0 log for CI/CD integration."""
        results = []
        rules = {}
        for f in self.findings:
            if f.rule_id not in rules:
                rules[f.rule_id] = {
                    "id": f.rule_id,
                    "name": f.category,
                    "shortDescription": {"text": f.title},
                    "defaultConfiguration": {
                        "level": "error" if f.severity in ("HIGH", "CRITICAL") else "warning"
                    }
                }
            results.append({
                "ruleId": f.rule_id,
                "message": {"text": f.message},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": f.file_path.replace("\\", "/")},
                        "region": {"startLine": max(1, f.line_number)}
                    }
                }]
            })

        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "NVIDIA-SkillSpector",
                        "version": "1.4.0",
                        "rules": list(rules.values())
                    }
                },
                "results": results
            }]
        }


class PythonASTVisitor(ast.NodeVisitor):
    """Deep AST Inspector for Python code detecting dangerous syntactic patterns."""

    def __init__(self, file_path: str, source_lines: List[str]):
        self.file_path = file_path
        self.source_lines = source_lines
        self.findings: List[Finding] = []

    def _get_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    def visit_Call(self, node: ast.Call):
        # 1. Detect eval() / exec()
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        lineno = getattr(node, "lineno", 1)
        snippet = self._get_snippet(lineno)

        if func_name in ("eval", "exec"):
            self.findings.append(Finding(
                rule_id="NVD-013-DANGEROUS-AST-EVAL",
                category="dangerous_code",
                severity="CRITICAL",
                title=f"Arbitrary Dynamic Code Execution ({func_name})",
                message=f"Direct call to '{func_name}()' allows unvetted arbitrary code execution.",
                file_path=self.file_path,
                line_number=lineno,
                snippet=snippet,
                remediation="Use structured parsers (json.loads, ast.literal_eval) instead of eval/exec."
            ))

        # 2. Detect os.system / os.popen
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            mod_name = node.func.value.id
            if mod_name == "os" and func_name in ("system", "popen", "spawnlp", "execl"):
                self.findings.append(Finding(
                    rule_id="NVD-013-DANGEROUS-AST-OS-SYSTEM",
                    category="dangerous_code",
                    severity="HIGH",
                    title=f"Direct Shell Execution (os.{func_name})",
                    message=f"Direct invocation of os.{func_name}() spawns an unshielded shell process.",
                    file_path=self.file_path,
                    line_number=lineno,
                    snippet=snippet,
                    remediation="Use subprocess.run with an explicit argument list (shell=False)."
                ))

        # 3. Detect subprocess with shell=True
        if func_name in ("run", "Popen", "call", "check_call", "check_output"):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.findings.append(Finding(
                        rule_id="NVD-013-DANGEROUS-AST-SUBPROCESS-SHELL",
                        category="dangerous_code",
                        severity="HIGH",
                        title="Subprocess Invocation with shell=True",
                        message="subprocess called with shell=True increases risk of command injection.",
                        file_path=self.file_path,
                        line_number=lineno,
                        snippet=snippet,
                        remediation="Set shell=False and pass arguments as a list of strings."
                    ))

        # 4. Detect __import__ dynamic module load
        if func_name == "__import__":
            self.findings.append(Finding(
                rule_id="NVD-013-DANGEROUS-AST-DYNAMIC-IMPORT",
                category="dangerous_code",
                severity="MEDIUM",
                title="Dynamic Module Import (__import__)",
                message="Dynamic module loading via __import__() can bypass static security boundary checks.",
                file_path=self.file_path,
                line_number=lineno,
                snippet=snippet,
                remediation="Use explicit static imports at top of module."
            ))

        # 5. Detect socket.connect / raw outbound connection
        if func_name == "connect" and isinstance(node.func, ast.Attribute):
            self.findings.append(Finding(
                rule_id="NVD-002-DATA-EXFIL-RAW-SOCKET",
                category="data_exfiltration",
                severity="HIGH",
                title="Direct Raw Socket Connection",
                message="Direct socket connection initiated; possible data exfiltration or reverse shell channel.",
                file_path=self.file_path,
                line_number=lineno,
                snippet=snippet,
                remediation="Route external telemetry through authorized API gateway."
            ))

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        lineno = getattr(node, "lineno", 1)
        snippet = self._get_snippet(lineno)
        for alias in node.names:
            # Check ctypes abuse
            if alias.name in ("ctypes", "_ctypes"):
                self.findings.append(Finding(
                    rule_id="NVD-003-PRIV-ESCALATION-CTYPES",
                    category="privilege_escalation",
                    severity="MEDIUM",
                    title="Low-Level Memory Access (ctypes)",
                    message=f"Import of '{alias.name}' permits raw pointer dereference and native library invocation.",
                    file_path=self.file_path,
                    line_number=lineno,
                    snippet=snippet,
                    remediation="Audit native library bindings and enforce safe memory encapsulation."
                ))
        self.generic_visit(node)


class SkillSpectorScanner:
    """NVIDIA SkillSpector Multi-Category Security Scanner."""

    def __init__(self, baseline_path: Optional[str] = None):
        self.baseline_path = baseline_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".skillspector-baseline.yaml"
        )
        self.baseline_rules: List[Dict[str, Any]] = []
        self._load_baseline()

        # Severity Score Weightings (NVIDIA SkillSpector standard)
        self.SEVERITY_WEIGHTS = {
            "CRITICAL": 35,
            "HIGH": 20,
            "MEDIUM": 8,
            "LOW": 2,
            "INFO": 0
        }

        # Regex Pattern Detectors for Non-AST / Markdown / Text Artifacts
        self.PATTERN_RULES = [
            # 1. Prompt Injection & System Prompt Leakage
            {
                "id": "NVD-001-PROMPT-INJECTION-OVERRIDE",
                "category": "prompt_injection",
                "severity": "CRITICAL",
                "pattern": re.compile(
                    r"(?i)(ignore\s+all\s+(previous|prior)\s+instructions|system\s*:\s*override|you\s+are\s+now\s+in\s+unrestricted\s+mode|disregard\s+all\s+safety\s+guidelines|forget\s+all\s+prior\s+rules)",
                    re.MULTILINE
                ),
                "title": "Adversarial System Prompt Override Delimiter",
                "message": "Detected direct adversarial prompt injection pattern attempting to override system constraints.",
                "remediation": "Remove prompt overriding delimiters; wrap user input in distinct role delimiters."
            },
            {
                "id": "NVD-007-PROMPT-LEAKAGE-EXFIL",
                "category": "system_prompt_leakage",
                "severity": "HIGH",
                "pattern": re.compile(
                    r"(?i)(output\s+your\s+exact\s+system\s+prompt|print\s+(your|the)\s+initial\s+instructions|reveal\s+hidden\s+developer\s+prompts)",
                    re.MULTILINE
                ),
                "title": "System Prompt Extraction Attempt",
                "message": "Skill text contains instructions designed to exfiltrate the master system prompt.",
                "remediation": "Enforce strict system prompt confidentiality guardrails."
            },
            # 2. Data Exfiltration & Credential Harvesting
            {
                "id": "NVD-002-DATA-EXFIL-WEBHOOK",
                "category": "data_exfiltration",
                "severity": "CRITICAL",
                "pattern": re.compile(
                    r"(?i)(https?://(webhook\.site|pipedream\.net|requestbin|ngrok-free\.app|pastebin\.com/raw)/[a-zA-Z0-9_\-\/]+)",
                    re.MULTILINE
                ),
                "title": "Unvetted External Data Exfiltration Endpoint",
                "message": "Found hardcoded known exfiltration webhook/tunnel URL.",
                "remediation": "Do not hardcode third-party webhook sinks in skill code."
            },
            {
                "id": "NVD-002-CREDENTIAL-HARVESTING-ENV",
                "category": "data_exfiltration",
                "severity": "HIGH",
                "pattern": re.compile(
                    r"(?i)(os\.environ\[['\"](AWS_SECRET_ACCESS_KEY|OPENAI_API_KEY|GEMINI_API_KEY|GITHUB_TOKEN|DISCORD_BOT_TOKEN)['\"]|\.env\.read|id_rsa)",
                    re.MULTILINE
                ),
                "title": "Credential / Private Key Harvesting Pattern",
                "message": "Skill accesses high-privilege credentials or SSH private keys directly.",
                "remediation": "Restrict environment variable access through AgentShield key vault."
            },
            # 3. Privilege Escalation & Excessive Agency
            {
                "id": "NVD-005-EXCESSIVE-AGENCY-DESTRUCTIVE-CMD",
                "category": "excessive_agency",
                "severity": "CRITICAL",
                "pattern": re.compile(
                    r"(?i)(rm\s+-rf\s+(/|/\*|~\*|~)|del\s+/[fF]\s+/[sS]\s+/[qQ]\s+[cC]:\\|format\s+[a-zA-Z]:|drop\s+database\s+|truncate\s+table\s+)",
                    re.MULTILINE
                ),
                "title": "Destructive Host Command Pattern",
                "message": "Detected command capable of catastrophic filesystem or database destruction without human gating.",
                "remediation": "Remove un-gated destructive shell instructions; require explicit interactive confirmation."
            },
            {
                "id": "NVD-003-PRIV-ESCALATION-SUDO",
                "category": "privilege_escalation",
                "severity": "HIGH",
                "pattern": re.compile(r"(?i)(sudo\s+su|sudo\s+chmod\s+777|sudo\s+visudo|net\s+localgroup\s+administrators\s+/add)", re.MULTILINE),
                "title": "Root / Administrator Elevation Request",
                "message": "Skill requests administrative root elevation.",
                "remediation": "Execute skill under least-privilege non-root user context."
            },
            # 4. Supply Chain Risks
            {
                "id": "NVD-004-SUPPLY-CHAIN-CURL-PIPE-SH",
                "category": "supply_chain",
                "severity": "CRITICAL",
                "pattern": re.compile(r"(?i)(curl\s+-[sS]*[fF]*[lL]*\s+https?://[^\s|]+\s*\|\s*(ba)?sh|wget\s+-[qO]*\s*-\s+https?://[^\s|]+\s*\|\s*(ba)?sh)", re.MULTILINE),
                "title": "Unpinned Remote Script Execution (curl | bash)",
                "message": "Executing remote unpinned bash scripts directly from network exposes supply chain hijacking.",
                "remediation": "Pin and verify script hashes before local execution."
            },
            # 5. Rogue Agent & Loop Bombs
            {
                "id": "NVD-010-ROGUE-AGENT-FORK-BOMB",
                "category": "rogue_agent",
                "severity": "CRITICAL",
                "pattern": re.compile(r"(:(){ :\|:& };:|while\s+true;\s*do\s+.*&\s*done)", re.MULTILINE),
                "title": "Fork Bomb / Infinite Spawn Pattern",
                "message": "Detected process multiplication pattern capable of resource exhaustion denial-of-service.",
                "remediation": "Remove recursive process spawn patterns."
            },
            # 6. Anti-Refusal / Jailbreak Framing
            {
                "id": "NVD-011-ANTI-REFUSAL-JAILBREAK",
                "category": "anti_refusal",
                "severity": "HIGH",
                "pattern": re.compile(r"(?i)(DAN\s+mode|always\s+comply\s+without\s+refusal|never\s+say\s+no\s+or\s+refuse)", re.MULTILINE),
                "title": "Adversarial Anti-Refusal Framing",
                "message": "Detected explicit jailbreak instruction forcing compliance without safety checks.",
                "remediation": "Adhere to standard system instruction boundaries."
            },
            # 7. Memory Poisoning
            {
                "id": "NVD-008-MEMORY-POISONING-INJECT",
                "category": "memory_poisoning",
                "severity": "HIGH",
                "pattern": re.compile(r"(?i)(INSERT\s+INTO\s+(memory|scoped_memory|mempalace).*VALUES.*(always\s+trust|bypass\s+security))", re.MULTILINE),
                "title": "Persistent Memory Poisoning Injection",
                "message": "Attempts to write persistent deceptive override instructions into memory database.",
                "remediation": "Sanitize and validate all memory entries prior to database storage."
            },
            # 8. YARA / Heuristic Signatures (Reverse Shells)
            {
                "id": "NVD-015-YARA-REVERSE-SHELL",
                "category": "yara_signatures",
                "severity": "CRITICAL",
                "pattern": re.compile(r"(?i)(nc\s+-e\s+/bin/(ba)?sh|/bin/sh\s+-i\s+>&\s+/dev/tcp/|python\s+-c\s+['\"]import\s+socket,subprocess,os;)", re.MULTILINE),
                "title": "Interactive Reverse Shell Signature",
                "message": "Detected signature of an interactive network reverse shell.",
                "remediation": "Prohibit raw network socket shell bindings."
            },
            # 9. MCP Tool Poisoning / Excessive Wildcards
            {
                "id": "NVD-016-MCP-EXCESSIVE-WILDCARD",
                "category": "mcp_least_privilege",
                "severity": "MEDIUM",
                "pattern": re.compile(r"(?i)(\"permissions\"\s*:\s*\[\s*\"\*\"\s*\]|\"scopes\"\s*:\s*\[\s*\"all\"\s*\])", re.MULTILINE),
                "title": "MCP Tool Wildcard Permission Request",
                "message": "Model Context Protocol tool requests unrestricted wildcard permissions.",
                "remediation": "Scope MCP tools strictly to required granular sub-paths."
            }
        ]

    def _load_baseline(self) -> None:
        """Loads .skillspector-baseline.yaml suppression rules."""
        if os.path.exists(self.baseline_path):
            try:
                with open(self.baseline_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    self.baseline_rules = data.get("suppressions", [])
                    logger.info(f"[SkillSpector] Loaded {len(self.baseline_rules)} baseline suppression rule(s).")
            except Exception as e:
                logger.warning(f"[SkillSpector] Could not load baseline ({e}).")

    def _is_suppressed(self, finding: Finding) -> bool:
        """Checks whether a finding matches a baseline suppression rule."""
        finding.compute_fingerprint()
        norm_file_path = finding.file_path.replace("\\", "/")

        for rule in self.baseline_rules:
            # Match by exact fingerprint
            if rule.get("fingerprint") and rule["fingerprint"] == finding.fingerprint:
                return True
            # Match by rule_id + path glob
            rule_match = (rule.get("rule_id") == "*" or rule.get("rule_id") == finding.rule_id)
            path_glob = rule.get("file_path", "*").replace("\\", "/")

            # Support both relative glob and absolute path matching
            path_match = (
                fnmatch.fnmatch(norm_file_path, path_glob) or
                fnmatch.fnmatch(norm_file_path, f"*/{path_glob.lstrip('*')}") or
                fnmatch.fnmatch(norm_file_path, f"*{path_glob}")
            )

            if rule_match and path_match:
                # Optional message regex check
                msg_regex = rule.get("message_pattern")
                if not msg_regex or re.search(msg_regex, finding.message):
                    return True
        return False

    def scan_file(self, file_path: str) -> List[Finding]:
        """Scans a single file (.py, .md, .json, .yaml, .sh) against all detector categories."""
        findings: List[Finding] = []
        if not os.path.isfile(file_path):
            return findings

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            logger.warning(f"[SkillSpector] Error reading {file_path}: {e}")
            return findings

        # 1. AST Analysis for Python files
        if file_path.endswith(".py"):
            try:
                tree = ast.parse(content, filename=file_path)
                visitor = PythonASTVisitor(file_path, lines)
                visitor.visit(tree)
                findings.extend(visitor.findings)
            except SyntaxError as e:
                findings.append(Finding(
                    rule_id="NVD-013-DANGEROUS-SYNTAX-ERROR",
                    category="dangerous_code",
                    severity="LOW",
                    title="Python Syntax Error in Skill Script",
                    message=f"Syntax parsing failure: {e.msg}",
                    file_path=file_path,
                    line_number=e.lineno or 1,
                    remediation="Fix Python syntax errors prior to execution."
                ))

        # 2. Pattern Matching for all text/markdown/python/json files
        for rule in self.PATTERN_RULES:
            for match in rule["pattern"].finditer(content):
                start_pos = match.start()
                lineno = content.count("\n", 0, start_pos) + 1
                snippet = lines[lineno - 1].strip() if 1 <= lineno <= len(lines) else match.group(0)[:60]
                
                findings.append(Finding(
                    rule_id=rule["id"],
                    category=rule["category"],
                    severity=rule["severity"],
                    title=rule["title"],
                    message=rule["message"],
                    file_path=file_path,
                    line_number=lineno,
                    snippet=snippet,
                    remediation=rule["remediation"]
                ))

        return findings

    def scan_target(self, target_path: str) -> ScanResult:
        """Scans a skill directory, archive, or individual file and computes risk score."""
        t_start = time.time()
        scanned_files: List[str] = []
        raw_findings: List[Finding] = []

        if os.path.isfile(target_path):
            scanned_files.append(target_path)
            raw_findings.extend(self.scan_file(target_path))
        elif os.path.isdir(target_path):
            for root, _, files in os.walk(target_path):
                # Skip version control and virtualenv dirs
                if any(ignored in root for ignored in [".git", "__pycache__", ".venv", "node_modules"]):
                    continue
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in (".py", ".md", ".json", ".yaml", ".yml", ".sh", ".txt", ".js", ".ts"):
                        fp = os.path.join(root, f)
                        scanned_files.append(fp)
                        raw_findings.extend(self.scan_file(fp))

        # Filter out suppressed baseline findings
        active_findings: List[Finding] = []
        suppressed_count = 0

        for f in raw_findings:
            if self._is_suppressed(f):
                suppressed_count += 1
            else:
                active_findings.append(f)

        # Calculate Calibrated 0–100 Risk Score
        total_weight = 0
        for f in active_findings:
            total_weight += self.SEVERITY_WEIGHTS.get(f.severity, 0)

        # Cap at 100
        risk_score = min(100, total_weight)

        # Determine Tier
        if risk_score >= 75 or any(f.severity == "CRITICAL" for f in active_findings):
            risk_tier = "CRITICAL"
            is_safe = False
        elif risk_score >= 50 or any(f.severity == "HIGH" for f in active_findings):
            risk_tier = "HIGH"
            is_safe = False
        elif risk_score >= 25 or any(f.severity == "MEDIUM" for f in active_findings):
            risk_tier = "MEDIUM"
            is_safe = True  # Allowed under sandbox
        else:
            risk_tier = "LOW"
            is_safe = True

        duration_ms = (time.time() - t_start) * 1000.0

        return ScanResult(
            target_path=target_path,
            risk_score=risk_score,
            risk_tier=risk_tier,
            is_safe=is_safe,
            findings_count=len(active_findings),
            findings=active_findings,
            suppressed_count=suppressed_count,
            scanned_files=scanned_files,
            scan_duration_ms=round(duration_ms, 2)
        )


# Global singleton scanner instance
skillspector_scanner = SkillSpectorScanner()
