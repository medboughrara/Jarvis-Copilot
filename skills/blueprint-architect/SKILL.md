---
name: blueprint-architect
description: "Generates system architecture blueprints, dataflow diagrams, and sequence models."
---

# System Blueprint & Architectural Design Playbook

When designing new software features, web HUD layouts, or hardware workflow dataflows:

1. **Mermaid Sequence & Component Diagrams**:
   - Model multi-component interactions using valid GitHub Markdown Mermaid syntax.
   - Enclose node labels in double quotes (`ROUTER --> CMP["🔗 Composio MCP Apps"]`).

2. **Interface Contract Specification**:
   - Define exact API request/response schemas before writing implementation code.
   - Document quantitative performance targets (e.g. latency < 500ms, VRAM < 4GB).
