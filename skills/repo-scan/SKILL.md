---
name: repo-scan
description: "In-depth workspace structure scanning, module boundary mapping, and file dependency ingestion."
---

# Repository Scan & Structural Ingestion Playbook

When ingesting or auditing repository codebases:

1. **Map Component Directories**:
   - Inspect module root paths (`agent/`, `tools/`, `voice/`, `ui/`, `skills/`).
   - Verify tool registration in `self.tools` within `agent/copilot.py`.

2. **Audit External Dependencies**:
   - Check `requirements.txt` for pinned dependencies and index URLs.
   - Verify environment variable requirements in `.env` and `config.py`.
