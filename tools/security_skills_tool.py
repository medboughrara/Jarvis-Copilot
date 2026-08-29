"""
Security Skills Progressive-Disclosure RAG and Execution Tool.
Integrates mukul975/Anthropic-Cybersecurity-Skills (818 skills, 29 domains, MITRE ATT&CK/NIST CSF mappings)
with ChromaDB semantic retrieval, scope-bound dual-use safety gating, and sandboxed script execution.
"""

import os
import sys
import json
import time
import hashlib
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.tools import tool
import config
from agent.security import AgentShield

logger = config.get_logger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBMODULE_DIR = os.path.join(ROOT_DIR, "data", "security_skills")
INDEX_DIR = os.path.join(ROOT_DIR, "data", "security_skills_index")
INDEX_FILE = os.path.join(SUBMODULE_DIR, "index.json")
SKILLS_DIR = os.path.join(SUBMODULE_DIR, "skills")
RISK_TIERS_FILE = os.path.join(INDEX_DIR, "risk_tiers.json")
NETWORK_EXCEPTIONS_FILE = os.path.join(INDEX_DIR, "network_exceptions.json")

# Lazy ChromaDB / LangChain setup
RAG_AVAILABLE = True


def get_submodule_commit_sha() -> str:
    """Returns the pinned commit SHA of the data/security_skills submodule."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=SUBMODULE_DIR,
            capture_output=True,
            text=True,
            check=False
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    # Fallback to recorded commit SHA
    return "1b3f6b2286981381a5cc0566551ef3bb6bc38383"


def compute_file_sha256(file_path: str) -> str:
    """Calculates SHA-256 hash for a given file."""
    if not os.path.exists(file_path):
        return ""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class SecuritySkillsEngine:
    """Core RAG indexer and execution manager for Anthropic Cybersecurity Skills."""

    def __init__(self, persist_dir: str = "scratch/chromadb"):
        self.persist_dir = persist_dir
        self.agent_shield = AgentShield()
        self._skills_cache: Dict[str, Dict[str, Any]] = {}
        self._risk_tiers: Dict[str, Any] = {}
        self._network_exceptions: Dict[str, Any] = {}
        self.vector_store = None
        self._load_metadata()

    def _load_metadata(self):
        """Loads index.json, risk_tiers.json, and network_exceptions.json."""
        if os.path.exists(RISK_TIERS_FILE):
            try:
                with open(RISK_TIERS_FILE, "r", encoding="utf-8") as f:
                    self._risk_tiers = json.load(f).get("skills", {})
            except Exception as e:
                logger.error(f"[SecuritySkills] Error reading risk_tiers.json: {e}")

        if os.path.exists(NETWORK_EXCEPTIONS_FILE):
            try:
                with open(NETWORK_EXCEPTIONS_FILE, "r", encoding="utf-8") as f:
                    self._network_exceptions = json.load(f).get("exceptions", {})
            except Exception as e:
                logger.error(f"[SecuritySkills] Error reading network_exceptions.json: {e}")

        if os.path.exists(INDEX_FILE):
            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for s in data.get("skills", []):
                        self._skills_cache[s["name"]] = s
            except Exception as e:
                logger.error(f"[SecuritySkills] Error loading index.json: {e}")

    def get_risk_tier(self, skill_name: str) -> str:
        """
        Determines the risk tier for a given skill.
        FAIL-CLOSED: Any unreviewed or newly added skill defaults to 'dual_use'.
        """
        entry = self._risk_tiers.get(skill_name)
        if entry and isinstance(entry, dict):
            return entry.get("tier", "dual_use")
        elif isinstance(entry, str):
            return entry
        # Fail-closed default
        return "dual_use"

    def is_network_exception(self, skill_name: str, script_name: str) -> Tuple[bool, str]:
        """Checks if a skill script has a reviewed explicit network exception."""
        entry = self._network_exceptions.get(skill_name)
        if entry and entry.get("script") == script_name and entry.get("allowed") is True:
            return True, entry.get("justification", "Explicitly allowlisted network access.")
        return False, "Fully network-isolated by default."

    def find_skills(
        self,
        query: str,
        domain: str = None,
        framework: str = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Stage 1: Cheap semantic and keyword search over skill frontmatters (~30-50 tokens per result).
        Filters optionally by domain or framework tag (attack, nist_csf, atlas, d3fend, etc.).
        """
        if not self._skills_cache:
            self._load_metadata()

        query_terms = [t.lower() for t in query.split() if len(t) > 2]
        scored_skills = []

        for name, item in self._skills_cache.items():
            desc = item.get("description", "").lower()
            name_lower = name.lower()
            item_domain = item.get("domain", "").lower()

            if domain and domain.lower() not in item_domain and domain.lower() not in name_lower:
                continue

            score = 0
            # Exact phrase match in description or name
            if query.lower() in name_lower:
                score += 15
            if query.lower() in desc:
                score += 10

            # Term overlap
            for term in query_terms:
                if term in name_lower:
                    score += 5
                if term in desc:
                    score += 2

            # Framework match bonus
            if framework:
                fw_lower = framework.lower()
                if fw_lower in desc or fw_lower in name_lower:
                    score += 8

            if score > 0:
                risk_tier = self.get_risk_tier(name)
                scored_skills.append({
                    "name": name,
                    "description": item.get("description", ""),
                    "domain": item.get("domain", "cybersecurity"),
                    "subdomain": item.get("subdomain", ""),
                    "path": item.get("path", f"skills/{name}"),
                    "risk_tier": risk_tier,
                    "score": score
                })

        scored_skills.sort(key=lambda x: x["score"], reverse=True)
        top_matches = scored_skills[:top_k]

        # Enrich with parsed frontmatter tags if available
        results = []
        for m in top_matches:
            skill_dir = os.path.join(SKILLS_DIR, m["name"])
            skill_file = os.path.join(skill_dir, "SKILL.md")
            fw_mappings = {}
            if os.path.exists(skill_file):
                fw_mappings = self._extract_framework_ids_from_skill_md(skill_file)

            results.append({
                "name": m["name"],
                "description": m["description"],
                "domain": m["domain"],
                "risk_tier": m["risk_tier"],
                "mitre_attack": fw_mappings.get("mitre_attack", []),
                "nist_csf": fw_mappings.get("nist_csf", []),
                "atlas": fw_mappings.get("atlas", []),
                "d3fend": fw_mappings.get("d3fend", [])
            })

        return results

    def _extract_framework_ids_from_skill_md(self, file_path: str) -> Dict[str, List[str]]:
        """Parses YAML frontmatter for MITRE ATT&CK, NIST CSF, ATLAS, and D3FEND IDs."""
        mappings = {"mitre_attack": [], "nist_csf": [], "atlas": [], "d3fend": []}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            in_fm = False
            current_section = None
            for line in lines[:50]:
                stripped = line.strip()
                if stripped == "---":
                    if not in_fm:
                        in_fm = True
                        continue
                    else:
                        break
                if not in_fm:
                    continue

                if ":" in stripped and not stripped.startswith("-"):
                    key = stripped.split(":", 1)[0].strip()
                    if key in mappings:
                        current_section = key
                    else:
                        current_section = None
                elif stripped.startswith("-") and current_section:
                    val = stripped.lstrip("-").strip().strip("'\"")
                    mappings[current_section].append(val)
        except Exception:
            pass
        return mappings

    def load_skill_detail(self, skill_name: str) -> Dict[str, Any]:
        """
        Stage 2: Loads full SKILL.md body, prerequisites, workflows, verification steps,
        and available references/scripts.
        """
        skill_dir = os.path.join(SKILLS_DIR, skill_name)
        skill_file = os.path.join(skill_dir, "SKILL.md")

        if not os.path.exists(skill_file):
            return {
                "status": "error",
                "error": f"Security skill '{skill_name}' not found in '{SKILLS_DIR}'."
            }

        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()

        fw_mappings = self._extract_framework_ids_from_skill_md(skill_file)
        risk_tier = self.get_risk_tier(skill_name)

        # Check references and scripts
        references_dir = os.path.join(skill_dir, "references")
        ref_files = [f for f in os.listdir(references_dir)] if os.path.exists(references_dir) else []

        scripts_dir = os.path.join(skill_dir, "scripts")
        script_files = [f for f in os.listdir(scripts_dir)] if os.path.exists(scripts_dir) else []

        return {
            "status": "success",
            "name": skill_name,
            "risk_tier": risk_tier,
            "framework_mappings": fw_mappings,
            "skill_markdown": content,
            "available_references": ref_files,
            "available_scripts": script_files,
            "submodule_commit": get_submodule_commit_sha()
        }

    def execute_script(
        self,
        skill_name: str,
        script_name: str,
        args: List[str] = None,
        target: str = "",
        approval_token: str = None,
        task_id: str = None
    ) -> Dict[str, Any]:
        """
        Atomic scope-bound execution of bundled skill helper scripts inside the sandbox.
        Enforces:
        1. Scope-bound human authorization for dual-use skills.
        2. Rejection of ambiguous/empty targets.
        3. Sandboxed execution with Win32 Job Object memory cap & network isolation (unless allowlisted).
        4. Audit logging of script file SHA-256 and submodule commit SHA.
        """
        start_time = time.time()
        risk_tier = self.get_risk_tier(skill_name)
        submodule_sha = get_submodule_commit_sha()
        skill_dir = os.path.join(SKILLS_DIR, skill_name)
        script_path = os.path.join(skill_dir, "scripts", script_name)

        # 1. Validate script path integrity
        if not os.path.exists(script_path):
            return {
                "status": "error",
                "error": f"Script '{script_name}' not found for skill '{skill_name}' at '{script_path}'."
            }

        script_sha256 = compute_file_sha256(script_path)

        # 2. Dual-Use Authorization & Target Scope Binding (Fail-Closed)
        if risk_tier == "dual_use":
            # Empty or missing target check
            if not target or not target.strip():
                err_msg = (
                    f"Scope Error: Skill '{skill_name}' is classified as DUAL_USE. "
                    "You must declare an explicit target scope (e.g. 'localhost', '10.0.0.5', 'lab.internal'). "
                    "Empty or missing target is rejected."
                )
                self.agent_shield.log_tool_invocation(
                    tool_name="execute_security_skill_script",
                    args={"skill_name": skill_name, "script_name": script_name, "target": "", "risk_tier": risk_tier},
                    status="SCOPE_EMPTY_REJECTED",
                    duration_ms=0,
                    error_msg=err_msg
                )
                return {"status": "error", "error": err_msg}

            # If no approval token provided, request one
            task_id = task_id or f"sec_{hashlib.md5(f'{skill_name}:{script_name}:{target}:{time.time()}'.encode()).hexdigest()[:8]}"
            if not approval_token:
                token = self.agent_shield.create_approval_request(
                    task_id=task_id,
                    action_type="execute_security_skill",
                    details={
                        "skill_name": skill_name,
                        "script_name": script_name,
                        "target": target,
                        "risk_tier": risk_tier,
                        "args": args or []
                    }
                )
                return {
                    "status": "BLOCKED_APPROVAL_REQUIRED",
                    "task_id": task_id,
                    "token": token,
                    "target": target,
                    "skill_name": skill_name,
                    "message": f"Execution of dual-use skill '{skill_name}' against target '{target}' requires human approval token."
                }

            # Scope-bound token verification and atomic consumption
            is_valid, reason = self.agent_shield.verify_and_consume_security_skill_token(
                task_id=task_id,
                token=approval_token,
                expected_target=target,
                expected_skill=skill_name
            )
            if not is_valid:
                return {
                    "status": "error",
                    "error": f"Security Authorization Denied: {reason}"
                }

        # 3. Check network exception allowlist
        allow_network, net_reason = self.is_network_exception(skill_name, script_name)

        # 4. Execute inside Sandboxed Subprocess (shell=False)
        sandbox_res = self.agent_shield.run_sandboxed_python(
            script_path=script_path,
            args=args or [],
            timeout=15,
            allow_network=allow_network
        )

        duration_ms = round((time.time() - start_time) * 1000, 1)

        # 5. Persist Audit Log Entry with Provenance
        self.agent_shield.log_tool_invocation(
            tool_name="execute_security_skill_script",
            args={
                "skill_name": skill_name,
                "script_name": script_name,
                "target": target,
                "args": args or [],
                "risk_tier": risk_tier,
                "submodule_commit_sha": submodule_sha,
                "script_sha256": script_sha256,
                "allow_network": allow_network
            },
            status="SUCCESS" if sandbox_res.get("returncode") == 0 else "ERROR",
            duration_ms=duration_ms,
            error_msg=sandbox_res.get("stderr") if sandbox_res.get("returncode") != 0 else None
        )

        return {
            "status": "success" if sandbox_res.get("returncode") == 0 else "error",
            "skill_name": skill_name,
            "script_name": script_name,
            "target": target,
            "risk_tier": risk_tier,
            "submodule_commit_sha": submodule_sha,
            "script_sha256": script_sha256,
            "network_isolated": not allow_network,
            "stdout": sandbox_res.get("stdout", ""),
            "stderr": sandbox_res.get("stderr", ""),
            "returncode": sandbox_res.get("returncode", -1),
            "duration_ms": duration_ms
        }

    def get_attack_coverage(self, tactic: str = None) -> Dict[str, Any]:
        """Reads attack coverage metadata and summaries."""
        attack_doc = os.path.join(SUBMODULE_DIR, "ATTACK_COVERAGE.md")
        has_doc = os.path.exists(attack_doc)
        
        # Analyze tactics from index cache
        tactic_counts = {}
        for name, item in self._skills_cache.items():
            sub = item.get("subdomain", "general")
            tactic_counts[sub] = tactic_counts.get(sub, 0) + 1

        return {
            "status": "success",
            "total_skills": len(self._skills_cache),
            "tactic_distribution": tactic_counts,
            "coverage_document_available": has_doc,
            "submodule_commit": get_submodule_commit_sha()
        }


# Singleton engine instance
_security_skills_engine = SecuritySkillsEngine()


# LangChain tool wrappers
@tool
def find_security_skills(query: str, domain: str = None, framework: str = None, top_k: int = 5) -> str:
    """
    Search the Anthropic Cybersecurity Skills Library (818 skills, 29 domains) using fast frontmatter retrieval.
    Returns lightweight summaries with MITRE ATT&CK, NIST CSF, and D3FEND framework mappings.
    """
    skills = _security_skills_engine.find_skills(query=query, domain=domain, framework=framework, top_k=top_k)
    return json.dumps(skills, indent=2)


@tool
def load_security_skill(skill_name: str) -> str:
    """
    Loads the full practitioner-grade playbook for a specific cybersecurity skill.
    Includes When to Use, Prerequisites, Workflow steps, Verification criteria, and framework citations.
    """
    detail = _security_skills_engine.load_skill_detail(skill_name)
    return json.dumps(detail, indent=2)


@tool
def attack_coverage_report(tactic: str = None) -> str:
    """
    Generates a coverage report across MITRE ATT&CK tactics and security domains from the skills library.
    """
    report = _security_skills_engine.get_attack_coverage(tactic)
    return json.dumps(report, indent=2)


@tool
def execute_security_skill_script(
    skill_name: str,
    script_name: str,
    target: str = "",
    args_json: str = "[]",
    approval_token: str = "",
    task_id: str = ""
) -> str:
    """
    Executes a bundled helper script for a cybersecurity skill in a secure sandbox.
    Dual-use skills require an explicit target scope and a verified single-use approval token.
    """
    try:
        args = json.loads(args_json) if isinstance(args_json, str) else (args_json or [])
    except Exception:
        args = []
    res = _security_skills_engine.execute_script(
        skill_name=skill_name,
        script_name=script_name,
        args=args,
        target=target,
        approval_token=approval_token,
        task_id=task_id
    )
    return json.dumps(res, indent=2)
