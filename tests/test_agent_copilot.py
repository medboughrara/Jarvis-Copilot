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
        self.assertTrue("power" in res.lower() or "tree" in res.lower())

    def test_datasheet_query_dispatch(self):
        res = asyncio.run(self.agent.process_query("Pull MG996R servomotor datasheet specs"))
        self.assertTrue("datasheet" in res.lower() or "spec" in res.lower())

    def test_compliance_query_dispatch(self):
        res = asyncio.run(self.agent.process_query("Check RoHS and FCC compliance for servomotors"))
        self.assertTrue("compliance" in res.lower() or "rohs" in res.lower())

    def test_gui_screen_query_dispatch(self):
        res = asyncio.run(self.agent.process_query("Parse active KiCad GUI screen layout"))
        self.assertTrue("screen" in res.lower() or "kicad" in res.lower())


if __name__ == "__main__":
    unittest.main()
