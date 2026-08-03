"""
Unit & Integration Tests for agent memory & search enhancement (Jarvis PCB Copilot).
"""

import asyncio
import unittest
from agent.copilot import JarvisAgent
from tools.reach_tool import search_component_datasheet
from unittest.mock import patch, MagicMock

class TestAgentMemoryAndSearch(unittest.TestCase):
    def setUp(self):
        self.agent = JarvisAgent()

    @patch('tools.reach_tool.DDGS')
    def test_sts_servomotor_datasheet(self, mock_ddgs):
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"title": "Feetech STS Series Datasheet", "body": "19.5 kg-cm at 7.4V"}
        ]
        res = search_component_datasheet.invoke({"query": "Could you get the data sheet of servomotor STS?"})
        self.assertIn("Feetech STS Series", res)
        self.assertIn("19.5 kg-cm", res)
        self.assertIn("7.4V", res)

    def test_context_conscious_followup_question(self):
        # Turn 1: Screen capture command
        res1 = asyncio.run(self.agent.process_query("Capture my screen and describe the current circuit"))
        self.assertTrue(len(res1) > 0)
        
        # Turn 2: Follow-up question referencing the captured image
        res2 = asyncio.run(self.agent.process_query("Is the power section in the captured image good?"))
        self.assertTrue(len(res2) > 0)
        self.assertIn("POWER", res1.upper())


if __name__ == "__main__":
    unittest.main()
