"""
Native Stdio Model Context Protocol (MCP) Server for Jarvis PCB Copilot.
Dynamically registers LangChain tools from JarvisAgent at startup, preserving parameter type annotations, defaults, and docstrings.
"""

import inspect
from typing import List, Any
from pydantic_core import PydanticUndefined

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
import config
from agent.copilot import JarvisAgent
from agent.workflows import run_full_pcb_audit

logger = config.get_logger(__name__)

# Initialize FastMCP Server
mcp = FastMCP(
    name="Jarvis-PCB-Copilot",
    instructions="Local hardware copilot for KiCad schematic review, IPC-2221 thermal loss, signal integrity, and servomotor compliance."
)


def register_langchain_tools_to_mcp(mcp_server: FastMCP, tools_list: List[Any]):
    """
    Dynamically registers LangChain StructuredTool objects with FastMCP.
    Inspects each tool's Pydantic args_schema to construct a typed wrapper callable
    that preserves parameter type annotations AND default values.
    """
    for tool_obj in tools_list:
        tool_name = tool_obj.name
        description = tool_obj.description or f"Executes {tool_name} tool."
        args_schema = getattr(tool_obj, "args_schema", None)

        if not args_schema:
            def make_simple_wrapper(t):
                def wrapper():
                    return t.invoke({})
                return wrapper
            fn = make_simple_wrapper(tool_obj)
            fn.__name__ = tool_name
            fn.__doc__ = description
            mcp_server.add_tool(fn)
            continue

        fields = args_schema.model_fields if hasattr(args_schema, "model_fields") else {}
        parameters = []

        for field_name, field_info in fields.items():
            param_type = field_info.annotation if field_info.annotation is not inspect.Parameter.empty else str

            default_val = inspect.Parameter.empty
            if field_info.default is not PydanticUndefined:
                default_val = field_info.default
            elif field_info.default_factory is not None:
                default_val = field_info.default_factory()

            parameters.append(
                inspect.Parameter(
                    name=field_name,
                    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=default_val,
                    annotation=param_type
                )
            )

        sig = inspect.Signature(parameters=parameters)

        def make_wrapper(target_tool):
            def wrapper(**kwargs):
                return target_tool.invoke(kwargs)
            return wrapper

        wrapper_fn = make_wrapper(tool_obj)
        wrapper_fn.__name__ = tool_name
        wrapper_fn.__doc__ = description
        wrapper_fn.__signature__ = sig

        mcp_server.add_tool(wrapper_fn)


# Create JarvisAgent instance and dynamically register tools at startup
agent = JarvisAgent()
register_langchain_tools_to_mcp(mcp, agent.tools)

# Register workflow tool explicitly
@mcp.tool()
def full_pcb_audit(file_path: str = "") -> dict:
    """Runs autonomous 6-stage hardware review (ERC, Power, Thermal, SI, Supply Chain)."""
    return run_full_pcb_audit(file_path)


if __name__ == "__main__":
    logger.info(f"Starting Jarvis PCB Copilot Stdio MCP Server ({len(agent.tools)} tools registered)...")
    mcp.run()
