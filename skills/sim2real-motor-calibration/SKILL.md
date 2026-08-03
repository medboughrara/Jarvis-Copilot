---
name: sim2real-motor-calibration
description: "Servomotor torque, current, and kinematic alignment for AutoPick robotic arm hardware."
---

# Sim2Real Motor Calibration Playbook

When analyzing servomotor kinematics or motor driver schematics for AutoPick:

1. **Torque & Voltage Matching**:
   - Verify **Feetech STS3215 / MG996R** operating voltage (6.0V - 7.4V).
   - Ensure stall current (up to 2.5A per motor) is handled by high-current copper traces and connectors.

2. **PWM Controller Verification**:
   - Verify **PCA9685** I2C address selection jumpers (default `0x40`).
   - Check OE (Output Enable) pin pull-down resistor to prevent motor twitching during MCU bootup.
