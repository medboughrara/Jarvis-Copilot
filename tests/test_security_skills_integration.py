"""
Integration and Safety Unit Tests for Anthropic Cybersecurity Skills Library in Jarvis-Copilot.
Validates:
1. Two-stage progressive disclosure retrieval (find_security_skills -> load_security_skill).
2. Scope-bound dual-use safety gating and atomic token verification (Task 1).
3. Fail-closed default for unclassified skills (Task 3).
4. Explicit declared network exceptions and default sandbox network cutoff (Task 4).
5. Audit logging with submodule commit SHA and script file SHA-256 (Task 5).
6. Submodule provenance validation in update utility (Task 2).
7. ATT&CK coverage reporting tool.
"""

import os
import sys
import json
import time
import hashlib
import sqlite3
import unittest
from unittest.mock import patch, MagicMock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.security_skills_tool import (
    SecuritySkillsEngine,
    find_security_skills,
    load_security_skill,
    attack_coverage_report,
    execute_security_skill_script,
    get_submodule_commit_sha,
    compute_file_sha256
)
from agent.security import AgentShield
import scripts.update_security_skills as update_script


class TestSecuritySkillsIntegration(unittest.TestCase):

    def setUp(self):
        self.engine = SecuritySkillsEngine()
        self.shield = AgentShield()

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary test skills from submodule directory."""
        import shutil
        for mock_dir in ["test-dual-use-skill", "test-isolated-skill", "test-prov-skill"]:
            p = os.path.join(ROOT_DIR, "data", "security_skills", "skills", mock_dir)
            if os.path.exists(p):
                try:
                    shutil.rmtree(p)
                except Exception:
                    pass

    def test_retrieval_and_two_stage_loading(self):
        """Tests that find_security_skills returns lightweight summaries and load_security_skill loads full body."""
        # Stage 1: Frontmatter search
        results = self.engine.find_skills(query="memory forensics volatility", top_k=5)
        self.assertTrue(len(results) > 0, "Expected search results for memory forensics")
        
        top_skill = results[0]
        self.assertIn("name", top_skill)
        self.assertIn("volatility", top_skill["name"].lower())
        self.assertIn("risk_tier", top_skill)
        self.assertIn("mitre_attack", top_skill)
        self.assertTrue(isinstance(top_skill["mitre_attack"], list))

        # Stage 2: Deep load
        detail = self.engine.load_skill_detail(top_skill["name"])
        self.assertEqual(detail.get("status"), "success")
        self.assertIn("skill_markdown", detail)
        self.assertIn("When to Use", detail["skill_markdown"])
        self.assertIn("Workflow", detail["skill_markdown"])
        self.assertIn("submodule_commit", detail)

    def test_unclassified_skill_defaults_to_gated(self):
        """Task 3: Any skill not present in risk_tiers.json must FAIL-CLOSED and default to 'dual_use'."""
        unknown_skill = "completely-unclassified-custom-skill"
        tier = self.engine.get_risk_tier(unknown_skill)
        self.assertEqual(tier, "dual_use", "Unclassified skills must default to dual_use (fail closed)")

        # Verify that an unclassified skill requires approval
        needs_approval = self.shield.requires_approval("execute_security_skill", {
            "skill_name": unknown_skill,
            "risk_tier": tier,
            "target": "10.0.0.1"
        })
        self.assertTrue(needs_approval, "Unclassified skill must require human approval before execution")

    def test_execute_security_skill_script_scope_binding(self):
        """
        Task 1: Scope-bound execution testing:
        - Correct-scope execution succeeds with valid token.
        - Scope mismatch (approved for lab.internal, executed on 8.8.8.8) fails and is audit-logged.
        - Empty target is rejected and gated.
        - Args injection is inert (shell=False).
        - Replay rejection prevents token reuse.
        """
        # Create a mock skill script for testing
        test_skill_dir = os.path.join(ROOT_DIR, "data", "security_skills", "skills", "test-dual-use-skill", "scripts")
        os.makedirs(test_skill_dir, exist_ok=True)
        test_script_path = os.path.join(test_skill_dir, "test_agent.py")
        with open(test_script_path, "w", encoding="utf-8") as f:
            f.write("import sys\nprint(f'EXECUTED TARGET: {sys.argv[1] if len(sys.argv) > 1 else None}')\n")

        # 1. Empty target rejected
        empty_target_res = self.engine.execute_script(
            skill_name="test-dual-use-skill",
            script_name="test_agent.py",
            target=""
        )
        self.assertEqual(empty_target_res["status"], "error")
        self.assertIn("Scope Error", empty_target_res["error"])

        # 2. Dual-use skill without token returns BLOCKED_APPROVAL_REQUIRED
        task_id = f"test_sec_{hashlib.md5(b'test_scope').hexdigest()[:8]}"
        gate_res = self.engine.execute_script(
            skill_name="test-dual-use-skill",
            script_name="test_agent.py",
            target="lab.internal",
            task_id=task_id
        )
        self.assertEqual(gate_res["status"], "BLOCKED_APPROVAL_REQUIRED")
        token = gate_res["token"]
        self.assertTrue(bool(token))

        # 3. Scope mismatch: Try using valid token with wrong target '8.8.8.8'
        mismatch_res = self.engine.execute_script(
            skill_name="test-dual-use-skill",
            script_name="test_agent.py",
            target="8.8.8.8",
            approval_token=token,
            task_id=task_id
        )
        self.assertEqual(mismatch_res["status"], "error")
        self.assertIn("Scope mismatch", mismatch_res["error"])

        # Verify audit log recorded the scope mismatch
        with sqlite3.connect(self.shield.audit_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, error_msg FROM audit_log WHERE status = 'SCOPE_MISMATCH_REJECTED' ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            self.assertIsNotNone(row, "Expected SCOPE_MISMATCH_REJECTED entry in audit log")
            self.assertIn("Scope mismatch", row[1])

        # 4. Correct scope execution succeeds
        # Generate fresh token for lab.internal
        task_id_2 = f"test_sec_{hashlib.md5(b'test_scope_2').hexdigest()[:8]}"
        token_2 = self.shield.create_approval_request(
            task_id=task_id_2,
            action_type="execute_security_skill",
            details={
                "skill_name": "test-dual-use-skill",
                "script_name": "test_agent.py",
                "target": "lab.internal",
                "risk_tier": "dual_use"
            }
        )
        valid_res = self.engine.execute_script(
            skill_name="test-dual-use-skill",
            script_name="test_agent.py",
            target="lab.internal",
            args=["lab.internal"],
            approval_token=token_2,
            task_id=task_id_2
        )
        self.assertEqual(valid_res["status"], "success")
        self.assertIn("EXECUTED TARGET: lab.internal", valid_res["stdout"])

        # 5. Token replay rejection: using token_2 again fails
        replay_res = self.engine.execute_script(
            skill_name="test-dual-use-skill",
            script_name="test_agent.py",
            target="lab.internal",
            approval_token=token_2,
            task_id=task_id_2
        )
        self.assertEqual(replay_res["status"], "error")
        self.assertIn("Token is not PENDING", replay_res["error"])

        # 6. Args shell injection safety (shell=False)
        task_id_3 = f"test_sec_{hashlib.md5(b'test_scope_3').hexdigest()[:8]}"
        token_3 = self.shield.create_approval_request(
            task_id=task_id_3,
            action_type="execute_security_skill",
            details={"skill_name": "test-dual-use-skill", "script_name": "test_agent.py", "target": "localhost", "risk_tier": "dual_use"}
        )
        injection_arg = "; rm -rf / ; calc.exe &"
        inject_res = self.engine.execute_script(
            skill_name="test-dual-use-skill",
            script_name="test_agent.py",
            target="localhost",
            args=[injection_arg],
            approval_token=token_3,
            task_id=task_id_3
        )
        self.assertEqual(inject_res["status"], "success")
        self.assertIn(f"EXECUTED TARGET: {injection_arg}", inject_res["stdout"])

    def test_network_exceptions_enforcement(self):
        """Task 4: Non-allowlisted scripts run with network disabled; allowlisted scripts run with network enabled."""
        # Non-allowlisted script attempting network connection
        non_allow_skill_dir = os.path.join(ROOT_DIR, "data", "security_skills", "skills", "test-isolated-skill", "scripts")
        os.makedirs(non_allow_skill_dir, exist_ok=True)
        isolated_script = os.path.join(non_allow_skill_dir, "net_test.py")
        with open(isolated_script, "w", encoding="utf-8") as f:
            f.write("import socket\ns = socket.socket()\n")

        task_id = f"test_iso_{hashlib.md5(b'test_iso').hexdigest()[:8]}"
        token = self.shield.create_approval_request(
            task_id=task_id,
            action_type="execute_security_skill",
            details={"skill_name": "test-isolated-skill", "script_name": "net_test.py", "target": "localhost", "risk_tier": "dual_use"}
        )
        res = self.engine.execute_script(
            skill_name="test-isolated-skill",
            script_name="net_test.py",
            target="localhost",
            approval_token=token,
            task_id=task_id
        )
        self.assertEqual(res["status"], "error")
        self.assertIn("RestrictedNetworkError", res["stderr"])

        # Allowlisted exception check
        is_allowed, reason = self.engine.is_network_exception("analyzing-tls-certificate-transparency-logs", "agent.py")
        self.assertTrue(is_allowed, "Certificate transparency log query script should be allowlisted")
        self.assertIn("crt.sh", reason)

    def test_audit_logging_provenance(self):
        """Task 5: Audit log contains submodule commit SHA and SHA-256 hash of the exact script."""
        test_skill_dir = os.path.join(ROOT_DIR, "data", "security_skills", "skills", "test-prov-skill", "scripts")
        os.makedirs(test_skill_dir, exist_ok=True)
        prov_script = os.path.join(test_skill_dir, "prov_test.py")
        with open(prov_script, "w", encoding="utf-8") as f:
            f.write("print('PROVENANCE_OK')\n")

        expected_file_sha = compute_file_sha256(prov_script)
        submodule_sha = get_submodule_commit_sha()

        task_id = f"test_prov_{hashlib.md5(b'test_prov').hexdigest()[:8]}"
        token = self.shield.create_approval_request(
            task_id=task_id,
            action_type="execute_security_skill",
            details={"skill_name": "test-prov-skill", "script_name": "prov_test.py", "target": "localhost", "risk_tier": "dual_use"}
        )
        res = self.engine.execute_script(
            skill_name="test-prov-skill",
            script_name="prov_test.py",
            target="localhost",
            approval_token=token,
            task_id=task_id
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["script_sha256"], expected_file_sha)
        self.assertEqual(res["submodule_commit_sha"], submodule_sha)

        # Query audit log to confirm provenance stored in database
        with sqlite3.connect(self.shield.audit_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT args_json FROM audit_log WHERE tool_name = 'execute_security_skill_script' AND status = 'SUCCESS' ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            args_data = json.loads(row[0])
            self.assertEqual(args_data.get("script_sha256"), expected_file_sha)
            self.assertEqual(args_data.get("submodule_commit_sha"), submodule_sha)

    def test_submodule_update_script_validation(self):
        """Task 2 & Task 3: Update script verifies submodule boundary, diffs commits, and warns on unreviewed skills."""
        current_sha = update_script.validate_submodule_boundary()
        self.assertTrue(bool(current_sha))
        self.assertEqual(len(current_sha), 40)

        # Analyze diff against self (should be zero diff)
        diff_res = update_script.analyze_diff(current_sha, current_sha)
        self.assertEqual(len(diff_res.get("added_skills", [])), 0)

    def test_attack_coverage_report(self):
        """Task 7: attack_coverage_report tool returns tactic distribution."""
        report = self.engine.get_attack_coverage()
        self.assertEqual(report["status"], "success")
        self.assertTrue(report["total_skills"] >= 800)
        self.assertTrue(report["coverage_document_available"])


if __name__ == "__main__":
    unittest.main()
