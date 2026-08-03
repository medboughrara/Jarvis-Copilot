---
name: emc-emi-hardening
description: "Rules and EMI mitigation strategies for passing FCC Part 15 Class B compliance."
---

# EMC / EMI Hardening Playbook

When performing FCC Part 15 compliance checks or schematic review for EMI mitigation:

1. **Decoupling Capacitor Placement**:
   - Place a **0.1µF MLCC ceramic capacitor** directly adjacent to every VCC/VDD pin on ICs (`STM32F405`, `PCA9685`).
   - Add **10µF Tantalum / Electrolytic bulk capacitors** near power connectors (`J1`).

2. **Signal Bus Hardening**:
   - Add **22Ω - 33Ω series damping resistors** on high-speed UART TX lines to suppress ringing.
   - Calculate I2C pull-up resistors to keep rise time $t_r$ within 300ns.

3. **Ground Plane Integrity**:
   - Maintain an unbroken ground plane under all digital signal and power switching traces.
