"""
Unit & Integration Tests for tools/omniparser_tool.py (AutoPick Jarvis Copilot).
"""

import unittest
import os
from tools.omniparser_tool import OmniParserTool, parse_screen_gui


class TestOmniParserTool(unittest.TestCase):
    def test_screen_capture_and_parse(self):
        parser = OmniParserTool()
        test_path = os.path.join(os.getcwd(), "scratch", "test_screen.png")
        result = parser.capture_and_parse(output_path=test_path)
        
        self.assertTrue("Screen Capture Analysis" in result or "screen" in result.lower())
        self.assertTrue(os.path.exists(test_path))

    def test_langchain_tool_invocation(self):
        result = parse_screen_gui.invoke({"action_context": "KiCad PCB Layout"})
        self.assertTrue(len(result) > 0)


if __name__ == "__main__":
    unittest.main()
