---
name: skill-comply
description: "Verifies compliance with workspace coding standards, architectural constraints, and project rules."
---

# Skill Compliance & Rule Verification Playbook

When verifying if proposed code edits or system designs comply with project rules:

1. **Check Explicit Constraints**:
   - Verify non-negotiable architectural boundaries (e.g. no blocking UI main loops, strictly scoped variable paths).
   - Ensure all public functions maintain docstrings and backward-compatible argument signatures.

2. **Validate Error Handling & Logging**:
   - Ensure exceptions are never swallowed silently without logging.
   - Verify API key secrets and credentials are sanitized before log output.

3. **Verify Contract Completeness**:
   - Enforce explicit return types (`dict`, `bool`, `str`) for all tool functions.
   - Confirm all imports are present in file headers prior to tool execution.
