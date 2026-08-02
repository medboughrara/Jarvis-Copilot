"""
Unit & Integration Tests for tools/omniparser_tool.py (AutoPick Jarvis Copilot).
"""

import unittest
from tools.omniparser_tool import OmniParserTool, parse_screen_gui


class TestOmniParserTool(unittest.TestCase):
    def test_capture_and_parse(self):
        parser = OmniParserTool()
        result = parser.capture_and_parse(output_path="d:/aaaassistan_pcb/scratch/test_screen.png")
        self.assertIn("captured your active screen", result)
        self.assertIn("Visual analysis identified", result)

    def test_langchain_tool_invocation(self):
        result = parse_screen_gui.invoke({"action_context": "KiCad PCB Layout"})
        self.assertTrue(len(result) > 0)


if __name__ == "__main__":
    unittest.main()
