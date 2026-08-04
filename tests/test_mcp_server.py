"""
Unit tests for mcp_server.py dynamic MCP tool registration and parameter default preservation.
"""

import inspect
import unittest
from typing import Any

# Compatibility aliases for mcp package version differences (McpError vs MCPError, AnyFunction)
try:
    import mcp.shared.exceptions
    if not hasattr(mcp.shared.exceptions, "McpError") and hasattr(mcp.shared.exceptions, "MCPError"):
        mcp.shared.exceptions.McpError = mcp.shared.exceptions.MCPError
    import mcp.types
    if not hasattr(mcp.types, "AnyFunction"):
        mcp.types.AnyFunction = Any
except Exception:
    pass

from fastmcp import FastMCP
from mcp_server import mcp, register_langchain_tools_to_mcp
from tools.thermal_tool import calculate_thermal_loss
from tools.kicad_tool import analyze_kicad_file


class TestMCPServer(unittest.TestCase):
    def test_dynamic_tool_registration(self):
        test_mcp = FastMCP(name="TestMCP")
        register_langchain_tools_to_mcp(test_mcp, [calculate_thermal_loss, analyze_kicad_file])

        # Verify tools registered
        tool_names = [t.name for t in test_mcp._tool_manager.list_tools()]
        self.assertIn("calculate_thermal_loss", tool_names)
        self.assertIn("analyze_kicad_file", tool_names)

    def test_parameter_defaults_preservation(self):
        """Verifies that omitted optional parameters receive exact schema default values at call time."""
        test_mcp = FastMCP(name="TestMCPDefaults")
        register_langchain_tools_to_mcp(test_mcp, [calculate_thermal_loss])

        # Get registered tool wrapper callable
        tool_entry = test_mcp._tool_manager.get_tool("calculate_thermal_loss")
        self.assertIsNotNone(tool_entry)

        # Inspect signature
        sig = inspect.signature(tool_entry.fn)
        self.assertIn("current_amps", sig.parameters)
        self.assertEqual(sig.parameters["current_amps"].default, 3.0)
        self.assertEqual(sig.parameters["trace_width_mils"].default, 30.0)

        # Execute tool function with omitted parameters
        result = tool_entry.fn()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["current_amps"], 3.0)
        self.assertEqual(result["data"]["trace_width_mils"], 30.0)


if __name__ == "__main__":
    unittest.main()
