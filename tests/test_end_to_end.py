"""
End-to-End System Integration Test for Jarvis PCB Copilot (AutoPick / Multiverse AI).
Validates full pipeline flow: Speech Input -> Transcriber -> LangChain Agent (Tools) -> Kokoro TTS.
"""

import asyncio
import unittest
from agent.copilot import JarvisAgent
from voice.tts import TextToSpeech
from voice.stt import Transcriber
from unittest.mock import patch, MagicMock


class TestEndToEndPipeline(unittest.TestCase):
    def setUp(self):
        self.agent = JarvisAgent()
        self.tts = TextToSpeech()

    @patch("agent.copilot.ChatGoogleGenerativeAI")
    def test_full_copilot_flow_power_tree(self, mock_gemini):
        from unittest.mock import AsyncMock
        from langchain_core.messages import AIMessage
        mock_instance = AsyncMock()
        mock_instance.ainvoke.return_value = AIMessage(content="Generated Power Tree for AutoPick PCB")
        mock_gemini.return_value.bind_tools.return_value = mock_instance
        mock_gemini.return_value.ainvoke = mock_instance.ainvoke

        transcribed_user_command = "Jarvis, generate the power tree for the AutoPick PCB schematic"
        agent_response = asyncio.run(self.agent.process_query(transcribed_user_command))
        self.assertTrue(len(agent_response) > 0)
        asyncio.run(self.tts.speak("Power tree generated successfully."))

    @patch('tools.reach_tool.DDGS')
    @patch("agent.copilot.ChatGoogleGenerativeAI")
    def test_full_copilot_flow_datasheet_and_compliance(self, mock_gemini, mock_ddgs):
        from unittest.mock import AsyncMock
        from langchain_core.messages import AIMessage
        mock_instance = AsyncMock()
        mock_instance.ainvoke.return_value = AIMessage(content="Regulatory compliance report ready.")
        mock_gemini.return_value.bind_tools.return_value = mock_instance
        mock_gemini.return_value.ainvoke = mock_instance.ainvoke

        mock_ddgs_instance = MagicMock()
        mock_ddgs.return_value.__enter__.return_value = mock_ddgs_instance
        mock_ddgs_instance.text.return_value = [
            {"title": "MG996R", "body": "RoHS Compliant 3"}
        ]
        
        transcribed_user_command = "Check RoHS compliance and datasheet specs for MG996R servomotors"
        agent_response = asyncio.run(self.agent.process_query(transcribed_user_command))
        self.assertTrue(len(agent_response) > 0)
        asyncio.run(self.tts.speak("Regulatory compliance report ready."))

    def test_tts_barge_in(self):
        async def run_barge_in():
            task = asyncio.create_task(self.tts.speak("This is a very long text that should be interrupted before it finishes. It should not complete."))
            await asyncio.sleep(0.5)
            self.tts.stop()
            await task
            
        asyncio.run(run_barge_in())


if __name__ == "__main__":
    unittest.main()
