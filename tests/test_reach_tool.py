"""
Unit & Integration Tests for tools/reach_tool.py (AutoPick Jarvis Copilot).
"""

import unittest
from tools.reach_tool import AgentReachTool, search_component_datasheet, check_compliance_status


class TestReachTool(unittest.TestCase):
    def test_search_datasheet(self):
        res = AgentReachTool.search_datasheet("MG996R servomotor")
        self.assertIn("MG996R", res)
        self.assertIn("Torque", res)

    def test_compliance_verification(self):
        report = AgentReachTool.verify_compliance("PCA9685 PWM Driver")
        self.assertIn("Regulatory Compliance Report", report)
        self.assertIn("RoHS", report)

    def test_langchain_tool_invocations(self):
        res1 = search_component_datasheet.invoke({"query": "STM32F405 MCU"})
        self.assertTrue(len(res1) > 0)

        res2 = check_compliance_status.invoke({"component_name": "MG996R"})
        self.assertIn("Sim2Real Servomotor Controller Pipeline", res2)


if __name__ == "__main__":
    unittest.main()
