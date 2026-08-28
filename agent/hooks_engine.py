"""
Event Hooks Lifecycle Engine for Jarvis Copilot.
Directly adapts OpenHuman's hook dispatcher (`src/openhuman/hooks/`).
Enables modular subscription to lifecycle events across all subsystems:
- on_user_message: Triggered when a new user query arrives
- on_tool_start: Triggered before any tool is invoked
- on_tool_end: Triggered after a tool completes execution
- on_agent_response: Triggered when Jarvis delivers a response
- on_error: Triggered on execution failures for automated recovery
"""

import time
import logging
from typing import Dict, List, Callable, Any
import config

logger = config.get_logger(__name__)

class HooksEngine:
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {
            "on_user_message": [],
            "on_tool_start": [],
            "on_tool_end": [],
            "on_agent_response": [],
            "on_error": [],
            "on_cron_tick": []
        }
        self._register_default_hooks()

    def _register_default_hooks(self):
        # Default telemetry and audit logging hook
        self.register("on_user_message", self._default_log_user_message)
        self.register("on_tool_end", self._default_log_tool_execution)
        self.register("on_error", self._default_log_error)

    def _default_log_user_message(self, context: Dict[str, Any]):
        msg = context.get("query", "")
        src = context.get("source", "web_chat")
        logger.debug(f"[Hook: on_user_message] From {src}: '{msg[:60]}...'")

    def _default_log_tool_execution(self, context: Dict[str, Any]):
        tool_name = context.get("tool_name", "unknown")
        duration = context.get("duration_ms", 0)
        logger.debug(f"[Hook: on_tool_end] Tool '{tool_name}' executed in {duration:.1f}ms")

    def _default_log_error(self, context: Dict[str, Any]):
        err = context.get("error", "Unknown error")
        component = context.get("component", "system")
        logger.warning(f"[Hook: on_error] Captured error in {component}: {err}")

    def register(self, event_name: str, handler: Callable):
        if event_name not in self.handlers:
            self.handlers[event_name] = []
        self.handlers[event_name].append(handler)

    def dispatch(self, event_name: str, context: Dict[str, Any]):
        if event_name not in self.handlers:
            return

        for handler in self.handlers[event_name]:
            try:
                handler(context)
            except Exception as e:
                logger.error(f"[Hooks Engine] Exception in handler '{handler.__name__}' for '{event_name}': {e}")


# Global Singleton Hooks Dispatcher
hooks = HooksEngine()
