"""
Presentation Formatter Layer for Jarvis PCB Copilot.
Converts structured tool result dictionaries into human-friendly ASCII text banners for CLI display
or spoken summary strings for voice output (main.py).
"""

from typing import Dict, Any


def format_tool_output_for_voice(result: Dict[str, Any]) -> str:
    """Returns concise spoken summary for voice output."""
    if not isinstance(result, dict):
        return str(result)
    return result.get("summary", str(result))


def format_tool_output_for_cli(result: Dict[str, Any]) -> str:
    """Renders formatted text or ASCII banner from structured result dict."""
    if not isinstance(result, dict):
        return str(result)

    summary = result.get("summary", "")
    data = result.get("data", {})
    verdict = data.get("verdict")

    lines = []
    if verdict:
        lines.append(f"Verdict: [{verdict}]")
    if summary:
        lines.append(summary)

    formatted_text = result.get("formatted")
    if formatted_text:
        return formatted_text

    return "\n".join(lines) if lines else str(result)
