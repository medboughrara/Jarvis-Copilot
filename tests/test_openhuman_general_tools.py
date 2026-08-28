"""
Unit tests for OpenHuman-inspired general-purpose modules in Jarvis:
- Memory Tree & Goals Kanban (tools/memory_tree_tool.py)
- TokenJuice Token Compression (tools/tokenjuice_tool.py)
- Workflows & Tinyflows Engine (tools/workflows_engine_tool.py)
- Multi-Channel Hub (tools/multichannel_hub_tool.py)
- Medulla Reflex Engine (agent/medulla_reflex.py)
"""

import os
import sys

sys.path.insert(0, os.path.abspath("."))

from tools.memory_tree_tool import (
    memory_tree_store, memory_tree_query,
    goals_kanban_upsert, goals_kanban_list,
    people_profile_upsert
)
from tools.tokenjuice_tool import tokenjuice_compress
from tools.workflows_engine_tool import workflow_create, workflow_list, workflow_execute
from tools.multichannel_hub_tool import channel_send_message, channel_list_status
from agent.medulla_reflex import medulla


def test_memory_tree_store_and_query():
    store_res = memory_tree_store.invoke({
        "path": "/research/6g_subthz",
        "title": "Sub-THz 6G RIS Arrays",
        "content": "Reconfigurable Intelligent Surfaces operating in the 140GHz band with metamaterial phase-shifters.",
        "category": "research",
        "tags": "6g, ris, terahertz",
        "importance": 9
    })
    assert store_res["status"] == "success"

    query_res = memory_tree_query.invoke({"query": "140GHz"})
    assert query_res["status"] == "success"
    assert len(query_res["data"]["nodes"]) > 0


def test_goals_kanban_upsert_and_list():
    goal_res = goals_kanban_upsert.invoke({
        "title": "Secure 3 Diamond Sponsors for STLC Tunisia",
        "description": "Pitch to Tunisie Telecom, Ooredoo, and Orange",
        "status": "in_progress",
        "priority": "urgent",
        "category": "ieee_stlc",
        "deadline": "2026-10-30",
        "progress": 40
    })
    assert goal_res["status"] == "success"

    list_res = goals_kanban_list.invoke({})
    assert list_res["status"] == "success"
    assert "in_progress" in list_res["data"]["columns"]


def test_people_profile_upsert():
    res = people_profile_upsert.invoke({
        "name": "Prof. Mérouane Debbah",
        "role_affiliation": "Professor at Khalifa University",
        "email": "merouane.debbah@ku.ac.ae",
        "notes": "Global pioneer in 6G and Large Language Models for communications",
        "tags": "keynote, 6g, ieee_fellow"
    })
    assert res["status"] == "success"


def test_tokenjuice_compress():
    raw_json = '{"user": {"name": "Alice", "id": 12345, "preferences": {"theme": "dark", "notifications": true, "extra_long_metadata": "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz"}}, "status": "active"}'
    res = tokenjuice_compress.invoke({"content": raw_json, "content_type": "json"})
    assert res["status"] == "success"
    assert res["data"]["compressed_tokens"] <= res["data"]["original_tokens"]


def test_workflows_engine():
    wf_res = workflow_create.invoke({
        "name": "Auto Sync Obsidian Briefing",
        "description": "Generates daily summary to Obsidian",
        "trigger_type": "manual",
        "trigger_config": "{}",
        "steps_json": '[{"step": 1, "action": "memory_tree_query", "args": {"query": "recent"}}]'
    })
    assert wf_res["status"] == "success"

    exec_res = workflow_execute.invoke({"workflow_id_or_name": "Auto Sync Obsidian Briefing"})
    assert exec_res["status"] == "success"
    assert exec_res["data"]["status"] == "completed"


def test_multichannel_hub():
    status_res = channel_list_status.invoke({})
    assert status_res["status"] == "success"
    assert status_res["data"]["total_channels"] >= 5

    send_res = channel_send_message.invoke({
        "channel": "discord",
        "target_recipient": "general-announcements",
        "message_content": "IEEE ComSoc STLC Tunisia Master Plan Ready!"
    })
    assert send_res["status"] == "success"


def test_medulla_reflex_triage():
    triage1 = medulla.triage_intent("Design a 4-layer STM32 PCB in KiCad with USB-C")
    assert triage1["route"] == "pcb_hardware_specialist"

    triage2 = medulla.triage_intent("What did we decide about the speakers in memory?")
    assert triage2["route"] == "memory_tree_and_goals"

    triage3 = medulla.triage_intent("Delete all databases and drop tables")
    assert triage3["requires_human_approval"] is True
