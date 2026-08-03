"""
Unit tests for agent/composio_router.py (Jarvis PCB Copilot).
"""

import unittest
from agent.composio_router import ComposioRouter
from tools.kicad_tool import analyze_kicad_file
from tools.thermal_tool import calculate_thermal_loss
from tools.github_tool import manage_github_issue

class TestComposioRouter(unittest.TestCase):
    def test_filter_tools_for_query(self):
        tools = [analyze_kicad_file, calculate_thermal_loss, manage_github_issue]
        router = ComposioRouter(tools)

        kicad_tools = router.filter_tools_for_query("analyze KiCad schematic")
        self.assertTrue(any(t.name == "analyze_kicad_file" for t in kicad_tools))

        github_tools = router.filter_tools_for_query("log issue on GitHub")
        self.assertTrue(any(t.name == "manage_github_issue" for t in github_tools))

if __name__ == "__main__":
    unittest.main()
