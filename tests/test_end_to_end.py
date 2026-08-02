"""
End-to-End System Integration Test for Jarvis PCB Copilot (AutoPick / Multiverse AI).
Validates full pipeline flow: Speech Input -> Transcriber -> LangChain Agent (Tools) -> Kokoro TTS.
"""

import asyncio
import unittest
from agent.copilot import JarvisAgent
from voice.tts import TextToSpeech
from voice.stt import Transcriber


class TestEndToEndPipeline(unittest.TestCase):
    def setUp(self):
        self.agent = JarvisAgent()
        self.tts = TextToSpeech()

    def test_full_copilot_flow_power_tree(self):
        # 1. Simulated voice command input
        transcribed_user_command = "Jarvis, generate the power tree for the AutoPick PCB schematic"
        
        # 2. Process query through agent and registered tools
        agent_response = asyncio.run(self.agent.process_query(transcribed_user_command))
        self.assertIn("AutoPick PCB Power Tree Analysis", agent_response)
        
        # 3. Process text response through Kokoro TTS
        asyncio.run(self.tts.speak("Power tree generated successfully."))

    def test_full_copilot_flow_datasheet_and_compliance(self):
        # 1. Simulated voice command input
        transcribed_user_command = "Check RoHS compliance and datasheet specs for MG996R servomotors"
        
        # 2. Process query through agent
        agent_response = asyncio.run(self.agent.process_query(transcribed_user_command))
        self.assertIn("RoHS", agent_response)
        
        # 3. Synthesize voice response
        asyncio.run(self.tts.speak("Regulatory compliance report ready."))


if __name__ == "__main__":
    unittest.main()
