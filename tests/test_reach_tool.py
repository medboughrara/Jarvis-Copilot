"""
Unit & Integration Tests for tools/reach_tool.py (AutoPick Jarvis Copilot).
"""

import unittest
from unittest.mock import patch, MagicMock
from tools.reach_tool import AgentReachTool, search_component_datasheet, check_compliance_status


class TestReachTool(unittest.TestCase):
    @patch('tools.reach_tool.DDGS')
    def test_search_datasheet(self, mock_ddgs):
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"title": "MG996R Datasheet", "body": "Stall Torque: 11kg/cm"}
        ]
        
        res = AgentReachTool.search_datasheet("MG996R servomotor")
        self.assertIn("MG996R", res)
        self.assertIn("Torque", res)

    def test_compliance_verification(self):
        report = AgentReachTool.verify_compliance("PCA9685 PWM Driver")
        self.assertEqual(report["status"], "success")
        self.assertIn("verdict", report["data"])

    @patch('tools.reach_tool.DDGS')
    def test_langchain_tool_invocations(self, mock_ddgs):
        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"title": "STM32F405 MCU", "body": "ARM Cortex-M4"}
        ]
        
        res1 = search_component_datasheet.invoke({"query": "STM32F405 MCU"})
        self.assertEqual(res1["status"], "success")

        mock_ddgs_instance.text.return_value = [
            {"title": "MG996R", "body": "RoHS Compliant"}
        ]
        res2 = check_compliance_status.invoke({"component_name": "MG996R"})
        self.assertEqual(res2["status"], "success")
        self.assertIn("verdict", res2["data"])


if __name__ == "__main__":
    unittest.main()
