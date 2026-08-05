---
name: agentic-engineering
description: "Guidelines and patterns for autonomous agentic task decomposition, subagent delegation, and tool routing."
---

# Agentic Engineering & Task Decomposition Playbook

When executing complex multi-step user goals autonomously:

1. **Task Decomposition & Intent Filtering**:
   - Break large user requests into discrete, verifiable sub-tasks.
   - Use dynamic tool scoping (`ComposioRouter`) to reduce context token overhead.

2. **Reflex & Instinct Evaluation**:
   - Evaluate automatic reflex rules before calling LLM APIs (`agent/instincts.py`).
   - Trigger quantitative pass/fail checks prior to generating natural language summaries.

3. **Verification & Fail-Fast Fallbacks**:
   - Run capability tests and verify return status codes (`status == "success"`).
   - Use multi-tier LLM key rotation and cloud fallback tiers when encountering rate limits (HTTP 429).
