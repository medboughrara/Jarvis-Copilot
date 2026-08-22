"""
Unit tests for mcp_server.py dynamic MCP tool registration and parameter default preservation.
"""

import os
import sys
import inspect
import unittest

sys.path.insert(0, os.path.abspath("."))

from mcp.server import MCPServer
from mcp_server import mcp, register_langchain_tools_to_mcp
from tools.thermal_tool import calculate_thermal_loss
from tools.kicad_tool import analyze_kicad_file


class TestMCPServer(unittest.TestCase):
    def test_dynamic_tool_registration(self):
        test_mcp = MCPServer(name="TestMCP")
        register_langchain_tools_to_mcp(test_mcp, [calculate_thermal_loss, analyze_kicad_file])

        # Verify tools registered
        tool_names = [t.name for t in test_mcp._tool_manager.list_tools()]
        self.assertIn("calculate_thermal_loss", tool_names)
        self.assertIn("analyze_kicad_file", tool_names)

    def test_parameter_defaults_preservation(self):
        """Verifies that omitted optional parameters receive exact schema default values at call time."""
        test_mcp = MCPServer(name="TestMCPDefaults")
        register_langchain_tools_to_mcp(test_mcp, [calculate_thermal_loss])

        # Get registered tool wrapper callable
        tool_entry = test_mcp._tool_manager.get_tool("calculate_thermal_loss")
        self.assertIsNotNone(tool_entry)

        # Inspect signature
        sig = inspect.signature(tool_entry.fn)
        self.assertIn("current_amps", sig.parameters)
        self.assertEqual(sig.parameters["current_amps"].default, 3.0)
        self.assertEqual(sig.parameters["trace_width_mils"].default, 30.0)


if __name__ == "__main__":
    unittest.main()
