"""
Unit & Integration Tests for agent/copilot.py (AutoPick Jarvis Copilot).
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import AIMessage
from agent.copilot import JarvisAgent


class TestJarvisAgent(unittest.TestCase):
    def setUp(self):
        self.agent = JarvisAgent()

    @patch("tools.reach_tool.AgentReachTool.search_datasheet", return_value="[Datasheet Specs]: MG996R Servomotor")
    @patch("tools.reach_tool.AgentReachTool.verify_compliance", return_value="[Compliance Report]: RoHS & FCC Certified")
    @patch("agent.copilot.ChatGoogleGenerativeAI")
    def test_power_tree_query_dispatch(self, mock_gemini, mock_comp, mock_search):
        mock_instance = AsyncMock()
        mock_instance.ainvoke.return_value = AIMessage(content="Generated Power Tree for AutoPick PCB")
        mock_gemini.return_value.bind_tools.return_value = mock_instance
        mock_gemini.return_value.ainvoke = mock_instance.ainvoke

        res = asyncio.run(self.agent.process_query("Show me the power tree for the AutoPick PCB"))
        self.assertTrue("power" in res.lower() or "tree" in res.lower() or "context" in res.lower())

    @patch("tools.reach_tool.AgentReachTool.search_datasheet", return_value="[Datasheet Specs]: MG996R Servomotor")
    @patch("tools.reach_tool.AgentReachTool.verify_compliance", return_value="[Compliance Report]: RoHS & FCC Certified")
    @patch("agent.copilot.ChatGoogleGenerativeAI")
    def test_datasheet_query_dispatch(self, mock_gemini, mock_comp, mock_search):
        mock_instance = AsyncMock()
        mock_instance.ainvoke.return_value = AIMessage(content="MG996R Servomotor Datasheet Specs")
        mock_gemini.return_value.bind_tools.return_value = mock_instance
        mock_gemini.return_value.ainvoke = mock_instance.ainvoke

        res = asyncio.run(self.agent.process_query("Pull MG996R servomotor datasheet specs"))
        self.assertTrue("datasheet" in res.lower() or "spec" in res.lower() or "mg996r" in res.lower())

    @patch("tools.reach_tool.AgentReachTool.search_datasheet", return_value="[Datasheet Specs]: MG996R Servomotor")
    @patch("tools.reach_tool.AgentReachTool.verify_compliance", return_value="[Compliance Report]: RoHS & FCC Certified")
    @patch("agent.copilot.ChatGoogleGenerativeAI")
    def test_compliance_query_dispatch(self, mock_gemini, mock_comp, mock_search):
        mock_instance = AsyncMock()
        mock_instance.ainvoke.return_value = AIMessage(content="Compliance Report for Servomotors")
        mock_gemini.return_value.bind_tools.return_value = mock_instance
        mock_gemini.return_value.ainvoke = mock_instance.ainvoke

        res = asyncio.run(self.agent.process_query("Check RoHS and FCC compliance for servomotors"))
        self.assertTrue("compliance" in res.lower() or "rohs" in res.lower() or "report" in res.lower())

    @patch("tools.reach_tool.AgentReachTool.search_datasheet", return_value="[Datasheet Specs]: MG996R Servomotor")
    @patch("tools.reach_tool.AgentReachTool.verify_compliance", return_value="[Compliance Report]: RoHS & FCC Certified")
    @patch("agent.copilot.ChatGoogleGenerativeAI")
    def test_gui_screen_query_dispatch(self, mock_gemini, mock_comp, mock_search):
        mock_instance = AsyncMock()
        mock_instance.ainvoke.return_value = AIMessage(content="Screen layout parsed successfully")
        mock_gemini.return_value.bind_tools.return_value = mock_instance
        mock_gemini.return_value.ainvoke = mock_instance.ainvoke

        res = asyncio.run(self.agent.process_query("Parse active KiCad GUI screen layout"))
        self.assertTrue("screen" in res.lower() or "kicad" in res.lower() or "parsed" in res.lower())


if __name__ == "__main__":
    unittest.main()
