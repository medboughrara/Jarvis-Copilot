"""
Unit & Integration Tests for agent/copilot.py (AutoPick Jarvis Copilot).
"""

import asyncio
import unittest
from agent.copilot import JarvisAgent


class TestJarvisAgent(unittest.TestCase):
    def setUp(self):
        self.agent = JarvisAgent()

    def test_power_tree_query_dispatch(self):
        res = asyncio.run(self.agent.process_query("Show me the power tree for the AutoPick PCB"))
        self.assertIn("AutoPick PCB Power Tree Analysis", res)

    def test_datasheet_query_dispatch(self):
        res = asyncio.run(self.agent.process_query("Pull MG996R servomotor datasheet specs"))
        self.assertIn("Datasheet", res)

    def test_compliance_query_dispatch(self):
        res = asyncio.run(self.agent.process_query("Check RoHS and FCC compliance for servomotors"))
        self.assertIn("Compliance Report", res)

    def test_gui_screen_query_dispatch(self):
        res = asyncio.run(self.agent.process_query("Parse active KiCad GUI screen layout"))
        self.assertIn("I captured your active screen", res)


if __name__ == "__main__":
    unittest.main()
