"""
Incremental Context Window Compressor for Jarvis PCB Copilot.
Optimizes LLM prompt token usage and prevents latency degradation in long conversation sessions.
"""

from typing import List, Dict, Any, Tuple


class ContextWindowCompressor:
    """Manages conversational history compression and token budgeting."""

    def __init__(self, max_history_turns: int = 6):
        self.max_history_turns = max_history_turns

    def compress_history(self, history: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], str]:
        """
        Trims and compresses conversation turns past max_history_turns into a memory summary.
        """
        if len(history) <= self.max_history_turns * 2:
            return history, ""

        # Extract older turns for summary
        older_turns = history[:-self.max_history_turns * 2]
        recent_turns = history[-self.max_history_turns * 2:]

        summary_parts = []
        for turn in older_turns:
            role = "User" if turn["role"] == "user" else "Jarvis"
            content_snippet = turn["content"][:80].replace("\n", " ")
            summary_parts.append(f"- {role}: {content_snippet}...")

        compact_summary = f"PREVIOUS SESSION CONTEXT SUMMARY:\n" + "\n".join(summary_parts)
        return recent_turns, compact_summary
