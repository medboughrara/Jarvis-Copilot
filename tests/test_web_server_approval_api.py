"""
Acceptance Tests for Web Server Approval API & Authorization Flow.
Validates:
1. Valid token from trusted origin approves task.
2. Single-use token enforcement (replay rejection).
3. Incorrect/forged token rejection (401).
4. Missing X-Jarvis-Approval-Token header rejection (400).
5. Cross-Origin / CSRF rejection for unauthorized origins (403).
6. Constant-time digest verification (secrets.compare_digest).
"""

import unittest
import secrets
from fastapi.testclient import TestClient
from web_server import app
from agent.security import agentshield
from agent.task_runner import task_runner, TaskNode


class TestWebServerApprovalAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.task_id = f"test_auth_{secrets.token_hex(4)}"
        # Setup a task in BLOCKED state
        node1 = TaskNode(
            id=f"{self.task_id}_s1",
            name="Restricted Operation",
            role="executor",
            action_type="delete_file",
            status="BLOCKED"
        )
        self.valid_token = agentshield.create_approval_request(
            self.task_id,
            "delete_file",
            {"file": "important_system_file.py"}
        )
        task_runner.store.save_task(
            self.task_id,
            "Delete restricted file",
            "general",
            "SINGLE_SPECIALIZED",
            [node1],
            approval_token=self.valid_token
        )

    def test_valid_token_from_trusted_origin_approves(self):
        headers = {
            "X-Jarvis-Approval-Token": self.valid_token,
            "Origin": "http://localhost:8000"
        }
        response = self.client.post(f"/api/tasks/{self.task_id}/approve", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")

    def test_single_use_token_replay_rejected(self):
        headers = {
            "X-Jarvis-Approval-Token": self.valid_token,
            "Origin": "http://localhost:8000"
        }
        # First use: 200 OK
        resp1 = self.client.post(f"/api/tasks/{self.task_id}/approve", headers=headers)
        self.assertEqual(resp1.status_code, 200)

        # Second use with exact same token: 401 Unauthorized (burned)
        resp2 = self.client.post(f"/api/tasks/{self.task_id}/approve", headers=headers)
        self.assertEqual(resp2.status_code, 401)
        self.assertIn("Invalid or expired", resp2.json().get("message", ""))

    def test_incorrect_token_rejected(self):
        fake_token = secrets.token_urlsafe(24)
        headers = {
            "X-Jarvis-Approval-Token": fake_token,
            "Origin": "http://localhost:8000"
        }
        response = self.client.post(f"/api/tasks/{self.task_id}/approve", headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_missing_header_rejected(self):
        headers = {
            "Origin": "http://localhost:8000"
        }
        # No X-Jarvis-Approval-Token header provided
        response = self.client.post(f"/api/tasks/{self.task_id}/approve", headers=headers, json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required 'X-Jarvis-Approval-Token' header", response.json().get("message", ""))

    def test_cross_origin_csrf_rejected(self):
        # Malicious third-party origin attempt
        headers = {
            "X-Jarvis-Approval-Token": self.valid_token,
            "Origin": "http://evil-attacker-website.com"
        }
        response = self.client.post(f"/api/tasks/{self.task_id}/approve", headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertIn("forbidden", response.json().get("message", "").lower())

    def test_constant_time_comparison_used(self):
        # Direct assertion on security module implementation
        import inspect
        source = inspect.getsource(agentshield.verify_and_consume_token)
        self.assertIn("secrets.compare_digest", source, "verify_and_consume_token MUST use secrets.compare_digest")


if __name__ == "__main__":
    unittest.main()
