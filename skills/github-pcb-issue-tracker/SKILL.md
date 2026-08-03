---
name: github-pcb-issue-tracker
description: "Playbook for logging KiCad ERC errors, thermal alerts, and supply chain warnings as GitHub issues."
---

# GitHub PCB Issue Tracker Playbook

When logging hardware schematic or PCB design bugs to GitHub:

1. **Categorize the Error**:
   - Assign appropriate labels (`hardware-erc`, `thermal-risk`, `supply-chain`, `decoupling-missing`).

2. **Formulate Issue Body**:
   - Include affected components (e.g., `U1 STM32F405`, `U3 AMS1117-3.3`).
   - Include exact error details (e.g. *Junction temperature exceeds 85°C* or *Floating enable pin*).

3. **Execute GitHub Issue Logger**:
   - Use `manage_github_issue` tool to persist the issue in `scratch/github_issues_log.json`.
