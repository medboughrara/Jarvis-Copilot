"""
Unit tests for tools/github_tool.py (Jarvis PCB Copilot).
"""

import unittest
import os
from tools.github_tool import manage_github_issue

class TestGitHubTool(unittest.TestCase):
    def test_manage_github_issue(self):
        res = manage_github_issue.invoke({
            "title": "Decoupling Capacitor Missing on U1",
            "body": "Add 0.1uF MLCC near VDD pin",
            "labels": "hardware-erc,high-priority"
        })
        self.assertIn("GITHUB ISSUE LOGGED", res)
        self.assertIn("Decoupling Capacitor Missing on U1", res)
        self.assertTrue(os.path.exists("scratch/github_issues_log.json"))

if __name__ == "__main__":
    unittest.main()
