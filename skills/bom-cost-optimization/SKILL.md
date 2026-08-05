---
name: bom-cost-optimization
description: "Playbook for cross-referencing LCSC and JLCPCB Basic vs Extended components to minimize manufacturing cost."
---

# BOM Cost & Sourcing Optimization Playbook

When optimizing the Bill of Materials (BOM) for PCB manufacturing:

1. **Prioritize Basic Parts on JLCPCB**:
   - Verify if passives (0603/0805 resistors, MLCC capacitors) and standard regulators (AMS1117-3.3, PCA9685) are tagged as **Basic Parts** on JLCPCB. Basic parts do not incur extra setup reel loading fees.

2. **Check Second-Source Substitutes**:
   - For extended or out-of-stock ICs, query `check_supply_chain_status` to find pin-compatible drop-in replacements.
