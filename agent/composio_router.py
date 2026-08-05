"""
Composio-Style On-Demand Dynamic Tool Router & Tool Stacker for Jarvis Copilot.
Filters tools dynamically based on prompt intent to keep LLM context lightweight and fast.
"""

from typing import List
from langchain_core.tools import BaseTool

class ComposioRouter:
    """Dynamically binds relevant tools based on query intent to reduce prompt bloat."""

    def __init__(self, all_tools: List[BaseTool]):
        self.all_tools = all_tools

    def filter_tools_for_query(self, query: str) -> List[BaseTool]:
        """Returns subset of tools relevant to user query intent."""
        query_lower = query.lower()

        # If general hardware inquiry or audit, bind full tool set
        if any(w in query_lower for w in ["audit", "workflow", "review", "help", "all tools", "capabilities"]):
            return self.all_tools

        matched_tools = []
        for tool in self.all_tools:
            name = tool.name.lower()
            desc = tool.description.lower()

            # Intent keywords matching
            if "kicad" in name or "schematic" in name:
                if any(w in query_lower for w in ["kicad", "schematic", "pcb", "net", "wire", "component"]):
                    matched_tools.append(tool)
            elif "power" in name or "thermal" in name:
                if any(w in query_lower for w in ["power", "voltage", "current", "heat", "thermal", "rail", "12v", "5v", "3.3v"]):
                    matched_tools.append(tool)
            elif "erc" in name or "error" in name or "compliance" in name:
                if any(w in query_lower for w in ["erc", "drc", "rule", "error", "rohs", "fcc", "compliance"]):
                    matched_tools.append(tool)
            elif "github" in name or "issue" in name:
                if any(w in query_lower for w in ["github", "issue", "ticket", "log", "repo"]):
                    matched_tools.append(tool)
            elif "bom" in name or "supply" in name or "stock" in name:
                if any(w in query_lower for w in ["bom", "part", "cost", "stock", "lcsc", "mouser", "digikey"]):
                    matched_tools.append(tool)
            elif "composio" in name:
                if any(w in query_lower for w in [
                    "email", "gmail", "send", "inbox", "slack", "notion", "calendar",
                    "composio", "app", "integration", "message", "schedule", "drive"
                ]):
                    matched_tools.append(tool)

        # Fallback to all tools if no specific match
        return matched_tools if matched_tools else self.all_tools

