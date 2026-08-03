"""
Unit tests for agent/workflows.py (Jarvis PCB Copilot).
"""

import unittest
import os
from agent.workflows import run_full_pcb_audit

class TestWorkflows(unittest.TestCase):
    def test_run_full_pcb_audit(self):
        res = run_full_pcb_audit("")
        self.assertIn(res["status"], ["PASSED", "WARNING", "FAILED"])
        self.assertIn("phases", res)
        self.assertTrue(os.path.exists("scratch/pcb_audit_report.json"))
        self.assertTrue(os.path.exists("scratch/pcb_audit_report.md"))

if __name__ == "__main__":
    unittest.main()
