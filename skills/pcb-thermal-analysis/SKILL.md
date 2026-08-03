---
name: pcb-thermal-analysis
description: "Guidelines and calculations for high-current copper trace power loss and regulator thermal dissipation."
---

# PCB Thermal Analysis Playbook

When analyzing PCB thermal loss or linear regulator power dissipation for the AutoPick robotic arm:

1. **Calculate IPC-2221 Current Density**:
   - Use `calculate_thermal_loss` tool to verify trace width in mils against motor current in Amps.
   - Target maximum trace temperature rise: **+10°C**.

2. **Evaluate Linear Regulators**:
   - Check input/output voltage differential ($V_{in} - V_{out}$).
   - Ensure junction temperature $T_j = T_a + (P_d \cdot R_{\theta JA})$ remains below **85°C** for long-term reliability (max silicon limit 125°C).

3. **Copper Thermal Vias**:
   - Recommend a 3x3 array of 0.3mm thermal vias under SOT-223 / TO-252 exposed GND pads to transfer heat to internal GND planes.
