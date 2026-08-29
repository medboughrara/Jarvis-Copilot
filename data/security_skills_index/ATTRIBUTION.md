# Attribution & License Notice — Anthropic Cybersecurity Skills Library

This repository vendors the **Anthropic-Cybersecurity-Skills** library (by mukul975) as a pinned Git submodule at `data/security_skills/`.

- **Upstream Repository:** [https://github.com/mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)
- **License:** Apache License 2.0 (see `data/security_skills/LICENSE`)
- **Pinned Commit:** `1b3f6b2286981381a5cc0566551ef3bb6bc38383`
- **Standard:** agentskills.io open skill specification
- **Total Skills:** 818 structured cybersecurity playbooks across 29 security domains
- **Framework Mappings:** MITRE ATT&CK, NIST CSF 2.0, MITRE ATLAS, D3FEND, NIST AI RMF, MITRE F3

## Safety & Authorized Use Policy
This library contains dual-use techniques (e.g. penetration testing, red teaming, adversary emulation playbooks) intended strictly for defensive engineering, detection development, and authorized assessments. Within Jarvis-Copilot:
1. All `dual_use` skills executed against real targets require explicit, cryptographically tokenized human approval.
2. Unclassified skills default to `dual_use` (fail closed).
3. All bundled scripts run in process-isolated, resource-capped sandboxes with network cutoff by default.
