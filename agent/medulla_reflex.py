"""
Split-Brain Medulla Engine for Jarvis AI Assistant.
Inspired by OpenHuman's split-brain architecture (Fast Reflex Triage + Deep Reasoning Core + Attention Queue).

Capabilities:
- Fast reflex intent classification without burning heavy LLM tokens
- Priority scoring and route selection (Reflex, Memory Tree, Multi-Agent Fleet, Tool Surface, Approval Gate)
- Attention Queue for items requiring user review or approval
"""

import re
import datetime
from typing import Dict, Any, List, Optional
import config

logger = config.get_logger(__name__)


class MedullaReflexEngine:
    """Fast reflex triage and attention manager for Jarvis."""

    def __init__(self):
        self.attention_queue: List[Dict[str, Any]] = []

    def triage_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Instantly triages user intent, scoring urgency, route, and suggested agent fleet.
        """
        text = user_input.strip().lower()
        now = datetime.datetime.now().isoformat()

        # 1. Approval Gate Detection
        if any(w in text for w in ["send email to all", "delete all", "drop database", "deploy to production", "purchase"]):
            return {
                "route": "approval_gate",
                "confidence": 0.95,
                "urgency": "high",
                "recommended_fleet": "Governance & Safety Officer",
                "requires_human_approval": True,
                "timestamp": now
            }

        # 2. PCB & Hardware Tasks
        if any(w in text for w in ["pcb", "kicad", "schematic", "footprint", "gerber", "drc", "erc", "routing", "spice", "bom", "3d model", "obj", "smd", "resistor", "capacitor"]):
            return {
                "route": "pcb_hardware_specialist",
                "confidence": 0.92,
                "urgency": "medium",
                "recommended_fleet": "KiCad EDA Specialist & 3D Modeler",
                "requires_human_approval": False,
                "timestamp": now
            }

        # 3. Memory & Goals Kanban Inquiries
        if any(w in text for w in ["remember", "recall", "what did we decide", "my goals", "kanban", "todo", "who is", "profile for", "memory tree", "obsidian"]):
            return {
                "route": "memory_tree_and_goals",
                "confidence": 0.90,
                "urgency": "low",
                "recommended_fleet": "Personal Knowledge Manager",
                "requires_human_approval": False,
                "timestamp": now
            }

        # 4. Web Search & Deep Research
        if any(w in text for w in ["search for", "find all details", "research", "crawl", "look up", "who are the speakers", "conference", "dossier", "ieee"]):
            return {
                "route": "deep_researcher",
                "confidence": 0.88,
                "urgency": "medium",
                "recommended_fleet": "Deep Web Researcher & Synthesizer",
                "requires_human_approval": False,
                "timestamp": now
            }

        # 5. External Workspace Apps (Notion, Google Sheets, Gmail, Discord)
        if any(w in text for w in ["google sheet", "sheets", "notion", "gmail", "email", "calendar", "discord", "slack", "composio"]):
            return {
                "route": "workspace_integrations",
                "confidence": 0.89,
                "urgency": "medium",
                "recommended_fleet": "Workspace Connector & API Agent",
                "requires_human_approval": False,
                "timestamp": now
            }

        # 6. Workflows & Automations
        if any(w in text for w in ["workflow", "routine", "automation", "cron", "schedule", "trigger"]):
            return {
                "route": "workflow_orchestrator",
                "confidence": 0.85,
                "urgency": "medium",
                "recommended_fleet": "Tinyflows Automation Engine",
                "requires_human_approval": False,
                "timestamp": now
            }

        # Default: Deep Reasoning Core
        return {
            "route": "deep_reasoning_core",
            "confidence": 0.75,
            "urgency": "normal",
            "recommended_fleet": "Jarvis General Super-Assistant Core",
            "requires_human_approval": False,
            "timestamp": now
        }

    def push_attention_item(self, title: str, description: str, action_type: str, payload: dict) -> Dict[str, Any]:
        """Pushes an item to the Attention Queue."""
        item = {
            "id": len(self.attention_queue) + 1,
            "title": title,
            "description": description,
            "action_type": action_type,
            "payload": payload,
            "status": "pending_review",
            "created_at": datetime.datetime.now().isoformat()
        }
        self.attention_queue.append(item)
        logger.info(f"[Medulla] Added Attention item #{item['id']}: '{title}'")
        return item

    def get_attention_queue(self) -> List[Dict[str, Any]]:
        """Returns pending attention items."""
        return [i for i in self.attention_queue if i["status"] == "pending_review"]


# Global instance
medulla = MedullaReflexEngine()
