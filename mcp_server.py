"""
Native Stdio Model Context Protocol (MCP) Server for Jarvis PCB Copilot.
Dynamically registers all LangChain tools from JarvisAgent at startup, preserving parameter type annotations, defaults, and docstrings.
"""

import sys
import inspect
from typing import List, Any
from pydantic_core import PydanticUndefined
from mcp.server import MCPServer
import config
from agent.copilot import JarvisAgent
from agent.workflows import run_full_pcb_audit

logger = config.get_logger(__name__)

# Initialize official MCP Server
mcp = MCPServer(
    name="Jarvis-PCB-Copilot",
    instructions="AI-native PCB design tool and hardware copilot for KiCad schematic review, IPC-2221 thermal loss, signal integrity, and manufacturing exports."
)


def register_langchain_tools_to_mcp(mcp_server: MCPServer, tools_list: List[Any]):
    """
    Dynamically registers LangChain StructuredTool objects with MCPServer.
    Inspects each tool's Pydantic args_schema to construct a typed wrapper callable
    that preserves parameter type annotations AND default values.
    """
    for tool_obj in tools_list:
        tool_name = tool_obj.name
        description = tool_obj.description or f"Executes {tool_name} tool."
        args_schema = getattr(tool_obj, "args_schema", None)

        if not args_schema:
            def make_simple_wrapper(t):
                def wrapper() -> dict:
                    return t.invoke({})
                return wrapper
            fn = make_simple_wrapper(tool_obj)
            fn.__name__ = tool_name
            fn.__doc__ = description
            mcp_server.tool(name=tool_name, description=description)(fn)
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

        sig = inspect.Signature(parameters=parameters, return_annotation=dict)

        def make_wrapper(target_tool):
            def wrapper(**kwargs) -> dict:
                return target_tool.invoke(kwargs)
            return wrapper

        wrapper_fn = make_wrapper(tool_obj)
        wrapper_fn.__name__ = tool_name
        wrapper_fn.__doc__ = description
        wrapper_fn.__signature__ = sig

        mcp_server.tool(name=tool_name, description=description)(wrapper_fn)


# Create JarvisAgent instance and dynamically register all tools at startup
agent = JarvisAgent()
register_langchain_tools_to_mcp(mcp, agent.tools)

# Register high-level workflow tool explicitly
@mcp.tool(name="full_pcb_audit", description="Runs autonomous 6-stage hardware review (ERC, Power, Thermal, SI, Supply Chain).")
def full_pcb_audit(file_path: str = "") -> dict:
    """Runs autonomous 6-stage hardware review (ERC, Power, Thermal, SI, Supply Chain)."""
    return run_full_pcb_audit(file_path)


if __name__ == "__main__":
    logger.info("Starting Jarvis PCB Copilot Stdio MCP Server...")
    mcp.run()
