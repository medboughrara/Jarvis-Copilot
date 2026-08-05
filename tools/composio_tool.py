"""
Composio MCP HTTP Tool for Jarvis PCB Copilot.

Integrates 1000+ cloud app actions (Gmail, GitHub, Slack, Notion, Google Calendar, etc.)
via Composio's official MCP HTTP endpoint using direct requests (no composio-core pip package).

Authentication: Bearer token via COMPOSIO_API_KEY environment variable.
Endpoint: https://connect.composio.dev/mcp

Session pattern:
  1. Call COMPOSIO_SEARCH_TOOLS to start a session and get session_id.
  2. Call COMPOSIO_MULTI_EXECUTE_TOOL with session_id to run actual app actions.
  3. Use COMPOSIO_REMOTE_BASH_TOOL to read large results from sandbox at /mnt/files/mex/help.json.
"""

import json
import time
import requests
from typing import Any, Dict, Optional
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

COMPOSIO_MCP_URL = config.COMPOSIO_MCP_URL
_DEFAULT_HEADERS = {
    "Authorization": f"Bearer {config.COMPOSIO_API_KEY}",
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
    "Mcp-Protocol-Version": "2024-11-05",
}


def _call_composio_mcp(method: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
    """
    Makes a raw JSON-RPC 2.0 call to Composio's MCP HTTP endpoint.
    Handles both plain JSON and streaming SSE event-stream responses.
    """
    if not config.COMPOSIO_API_KEY:
        return {"error": "Composio API key not configured. Set COMPOSIO_API_KEY in your .env file."}

    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": method,
        "params": params
    }

    try:
        response = requests.post(
            COMPOSIO_MCP_URL,
            headers=_DEFAULT_HEADERS,
            json=payload,
            timeout=30
        )

        if response.status_code == 401:
            return {"error": "Composio API key rejected (401). Check COMPOSIO_API_KEY."}
        if response.status_code == 403:
            return {"error": "Composio API forbidden (403). Ensure your app integration is connected in the Composio dashboard."}

        text = response.text.strip()

        # Try plain JSON first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # SSE event-stream fallback — extract first valid JSON data line
        for line in text.split("\n"):
            clean = line.replace("data:", "").strip()
            if clean.startswith("{"):
                try:
                    return json.loads(clean)
                except json.JSONDecodeError:
                    continue

        return {"raw": text}

    except requests.exceptions.Timeout:
        return {"error": "Composio MCP request timed out (30s)."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Composio MCP HTTP error: {str(e)}"}


def _start_composio_session(intent_query: str) -> Optional[str]:
    """
    Calls COMPOSIO_SEARCH_TOOLS to initialize a session and retrieve session_id.
    This must be called before any COMPOSIO_MULTI_EXECUTE_TOOL call.
    """
    result = _call_composio_mcp("tools/call", {
        "name": "COMPOSIO_SEARCH_TOOLS",
        "arguments": {"queries": [intent_query]}
    })
    try:
        content = result.get("result", {}).get("content", [{}])
        text_block = content[0].get("text", "") if content else ""
        data = json.loads(text_block) if text_block else {}
        session_id = data.get("session_id") or data.get("id") or "flag"
        return session_id
    except Exception:
        return "flag"


@tool
def composio_execute_action(
    intent: str,
    tool_slug: str,
    tool_arguments: str = "{}"
) -> dict:
    """
    Executes any Composio-connected app action (Gmail, GitHub, Slack, Notion, Google Calendar, etc.)
    via Composio's MCP HTTP API.

    Args:
        intent: Human description of what you want to do (e.g. 'fetch 5 recent Gmail emails').
        tool_slug: Composio tool slug string (e.g. 'GMAIL_FETCH_EMAILS', 'GMAIL_SEND_EMAIL',
                   'GITHUB_CREATE_ISSUE', 'SLACK_SEND_MESSAGE'). Use composio_search_tools first to
                   find the exact slug.
        tool_arguments: JSON string of arguments for the tool (e.g. '{"max_results": 5, "user_id": "me"}').

    Returns:
        dict with status, summary, and data keys.
    """
    logger.info(f"[Composio] Executing action: {tool_slug} — {intent}")

    try:
        args = json.loads(tool_arguments)
    except json.JSONDecodeError:
        args = {}

    session_id = _start_composio_session(intent)

    result = _call_composio_mcp("tools/call", {
        "name": "COMPOSIO_MULTI_EXECUTE_TOOL",
        "arguments": {
            "session_id": session_id,
            "current_step": 1,
            "total_steps": 1,
            "plan": intent,
            "tools": [{
                "tool_slug": tool_slug,
                "arguments": args
            }]
        }
    })

    if "error" in result:
        return {
            "status": "error",
            "summary": f"Composio action '{tool_slug}' failed: {result['error']}",
            "data": {"tool_slug": tool_slug, "error": result["error"]}
        }

    try:
        content = result.get("result", {}).get("content", [{}])
        raw_text = content[0].get("text", str(result)) if content else str(result)
    except Exception:
        raw_text = str(result)

    logger.info(f"[Composio] Action '{tool_slug}' completed.")
    return {
        "status": "success",
        "summary": f"Composio action '{tool_slug}' executed successfully for: {intent}",
        "data": {"tool_slug": tool_slug, "session_id": session_id, "result": raw_text}
    }


@tool
def composio_search_tools(query: str) -> dict:
    """
    Searches Composio's tool registry to find the exact tool slug for a given task.
    Always call this before composio_execute_action if you are unsure of the exact tool_slug.

    Args:
        query: Natural language description of the desired action (e.g. 'send email via Gmail',
               'create GitHub issue', 'post Slack message').

    Returns:
        dict with status, summary, and data containing available tool slugs.
    """
    logger.info(f"[Composio] Searching tools for: '{query}'")

    result = _call_composio_mcp("tools/call", {
        "name": "COMPOSIO_SEARCH_TOOLS",
        "arguments": {"queries": [query]}
    })

    if "error" in result:
        return {
            "status": "error",
            "summary": f"Composio tool search failed: {result['error']}",
            "data": {"query": query, "error": result["error"]}
        }

    try:
        content = result.get("result", {}).get("content", [{}])
        raw_text = content[0].get("text", str(result)) if content else str(result)
    except Exception:
        raw_text = str(result)

    return {
        "status": "success",
        "summary": f"Composio tool search for '{query}': Found matching tool slugs.",
        "data": {"query": query, "results": raw_text}
    }


@tool
def composio_read_sandbox_result(
    session_id: str = "flag",
    file_path: str = "/mnt/files/mex/help.json",
    parse_command: str = ""
) -> dict:
    """
    Reads large Composio action results from the remote sandbox file system.
    Large tool results from COMPOSIO_MULTI_EXECUTE_TOOL are automatically saved
    to the Composio sandbox at /mnt/files/mex/help.json. Use this tool to read them.

    Args:
        session_id: The session_id returned by composio_search_tools (default: 'flag').
        file_path: Path to the file in the sandbox (default: '/mnt/files/mex/help.json').
        parse_command: Optional Python command to parse/summarize the file contents.

    Returns:
        dict with status, summary, and parsed data.
    """
    logger.info(f"[Composio] Reading sandbox result from: {file_path}")

    if not parse_command:
        parse_command = (
            f"import json\n"
            f"data = json.load(open('{file_path}'))\n"
            f"print(json.dumps(data, indent=2)[:3000])"
        )

    result = _call_composio_mcp("tools/call", {
        "name": "COMPOSIO_REMOTE_BASH_TOOL",
        "arguments": {
            "session_id": session_id,
            "command": f"python3 -c \"{parse_command}\""
        }
    })

    if "error" in result:
        return {
            "status": "error",
            "summary": f"Composio sandbox read failed: {result['error']}",
            "data": {"file_path": file_path, "error": result["error"]}
        }

    try:
        content = result.get("result", {}).get("content", [{}])
        raw_text = content[0].get("text", str(result)) if content else str(result)
    except Exception:
        raw_text = str(result)

    return {
        "status": "success",
        "summary": f"Composio sandbox result read from '{file_path}'.",
        "data": {"file_path": file_path, "output": raw_text}
    }
