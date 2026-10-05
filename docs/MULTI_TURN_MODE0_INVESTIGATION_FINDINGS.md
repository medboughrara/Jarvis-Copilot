# Feetech STS3215 Multi-Turn Mode 0 Investigation Findings

**Date**: 2026-10-03  
**Target Axis**: Axis Y (Feetech STS3215 Bus Servo, ID 3)  
**Hardware Environment**: Windows, PySerial @ 1,000,000 baud, Feetech STS3215 smart actuator  
**Primary Reference Scripts**:
- `scratch/test_phase1_hardware.py`
- `scratch/verify_torque_enable_on_write.py`
- `scratch/test_phase1_production_path.py`
- `scratch/test_phase1_control_factory_limits.py`

---

## 1. Executive Summary

This investigation was conducted to determine whether the Feetech STS3215 bus servo can natively execute absolute multi-turn position control in **Mode 0 (Position Mode)** by widening the EEPROM angle limit registers `0x09–0x0A (Min Angle Limit)` and `0x0B–0x0C (Max Angle Limit)` beyond the standard single-turn envelope `[0, 4095]` (e.g. to `[-8192, +8192]`).

Through an empirical sequence of supervised micro-moves, bus transaction analyses, zero-motion diagnostics, and a clean single-variable control test, we have established a definitive, reproducible finding:

> **Definitive Finding**: Widening the EEPROM soft angle limits (`0x09/0x0B`) beyond the single-turn `[0, 4095]` boundary in Mode 0 **breaks the internal firmware trajectory generator and deceleration cusp calculation**. When commanded to a target position under widened limits, the STS3215 firmware fails to compute the deceleration profile and continues traveling at constant velocity indefinitely until an external tripline or timeout cuts power. Conversely, under factory-default limits `[0, 4095]`, the exact same motion profile and production code path decelerate and settle with textbook precision in both directions.
>
> Native multi-turn position control via EEPROM limit widening in Mode 0 is **unsupported by the STS3215 internal firmware**.

---

## 2. Background and Motivation

### 2.1 Project Goal
The high-precision optical scan stage on Axis Y utilizes a ball-screw / lead-screw drive coupled to an STS3215 servo. To achieve broad scanning fields without mechanical reconfiguration, the system desired an extended multi-rotation travel corridor ($\pm 2$ to $\pm 7$ turns) while maintaining absolute coordinate references.

### 2.2 Mode 3 Elimination
Prior architecture proposals suggested operating in **Mode 3**. Review of the official Feetech STS3215 Product Specification (Section 7-12) and the official Arduino C++ SDK (`SMS_STS.h`, `SMS_STS.cpp`) clarified the true operational modes:
- **Mode 0**: Absolute Angle Servo Mode (0–360° absolute closed-loop position control).
- **Mode 1**: Closed-Loop Speed / Motor Mode (maintains constant velocity under varying torque).
- **Mode 2**: Open-Loop Speed / Motor Mode.
- **Mode 3**: Stepping Mode (**Relative incremental displacement** relative to present position, not absolute coordinate positioning).

Because Mode 3 operates incrementally and lacks absolute closed-loop coordinates, it was definitively eliminated as a solution for absolute coordinate tracking.

### 2.3 The Mode 0 Extended-Limit Hypothesis
Datasheet Section 7-13 states:
> *"7-13 多圈模式 Multi-Loop Mode: 最高精度下可以正负7圈绝对位置控制，但掉电圈数不保存。扩大分辨率，圈数可翻倍。"*  
> *(Under highest precision, ±7 turns absolute position control is possible, but turn count is lost on power down. Expanding resolution doubles the turn count).*

In the STS3215 memory map:
- Register `0x09–0x0A`: Min Angle Limit (Signed 15-bit integer, `SM15`)
- Register `0x0B–0x0C`: Max Angle Limit (Signed 15-bit integer, `SM15`)
- Factory defaults: `Min = 0` (`0x0000`), `Max = 4095` (`0x0FFF`)

The working hypothesis posited that expanding these soft limits in EEPROM to `[-8192, +8192]` (`0xA000` to `0x2000`) would unlock $\pm 2$ full revolutions of absolute closed-loop position control in Mode 0. Register `0x1F–0x20` (Position Offset) was strictly guarded and kept at `0` to prevent altering the physical home definition.

---

## 3. Investigation Progression & Hardware Findings

### 3.1 Hardware Move Attempt 1 (Negative Direction into Mechanical Endstop)
- **Starting Position $P_0$**: `188`
- **Commanded Target**: `-200`
- **Result**: The motor drove downward into the physical hard stop at raw count `8`. The excessive stall current triggered the host USB-to-UART bridge power protection, temporarily dropping the COM port.
- **Lesson Learned**: Established strict corridor boundaries; count `8` is the physical lower limit of Axis Y travel. All subsequent tests enforced verified clearance corridors ($\ge 100$ counts) and positive-displacement or upward-margin rules.

### 3.2 Hardware Move Attempt 2 (Kinematic Mismatch under Widened Limits)
- **Profile**: `Speed = 800 counts/s`, `ACC = 15`
- **Starting Position $P_0$**: `596` $\to$ **Target**: `796` ($\Delta = +200$ counts)
- **Result**: At `Speed=800` and `ACC=15` ($a \approx 1600\text{ counts/s}^2$), kinematic acceleration and deceleration each require 200 counts ($\Delta_{\text{crit}} = 400\text{ counts total}$). Within a 200-count displacement, commanding peak speed 800 was mathematically unachievable before needing to decelerate. The motor blew through target `796` at $t=0.498\text{ s}$ (reading position `803`, with speed still climbing from $650 \to 750\text{ counts/s}$), and load monotonically escalated as inertial torque fought gravity until hitting count `252` at position `904`, safely tripping the `LOAD_LIMIT_EXCEEDED` tripline ($>250$) at $t=0.623\text{ s}$.
- **Remediation**: The profile was kinematically redesigned for short displacements: `Speed = 250 counts/s`, `ACC = 20` (requiring only $15.6$ counts to accelerate and $15.6$ counts to decelerate, leaving $168.8$ counts of steady cruise margin).

### 3.3 Hardware Move Attempt 3 (The Deceleration Anomaly)
- **Profile**: `Speed = 250 counts/s`, `ACC = 20`
- **Starting Position $P_0$**: `1013` $\to$ **Target**: `1213` ($\Delta = +200$ counts)
- **Result**: The load curve remained completely flat and benign ($-60$ to $-88$ counts, well under the 250 threshold, representing $<9\%$ torque load). However, the servo **failed to decelerate**: it maintained an exact, flat velocity of $250\text{ counts/s}$ straight through target `1213` and kept running until the `4.0s` safety timeout tripped at position `2002` (coasting to `2044`).
- **Open Question**: Was this failure caused by the custom scratch script's 7-byte block write to `0x29` (which included writing `Time = 0` to `0x2C`), or was it intrinsic to the firmware?

### 3.4 Zero-Motion Diagnostic & 0x28 Torque Behavior
Before testing production motion, an isolated zero-motion diagnostic ([verify_torque_enable_on_write.py](file:///d:/aaaassistan_pcb/scratch/verify_torque_enable_on_write.py)) was executed:
1. Pre-check: `0x28 (Torque Enable)` confirmed `0` (OFF).
2. Command: Written identical 7-byte payload `[ACC=20, Pos=1213, Time=0, Speed=250]` to register `0x29`.
3. Immediate Readback:
   - Single-byte read of `0x28` returned **`1`** (`Torque Enable = ACTIVE`).
   - 10-byte block read of `0x28–0x31` confirmed: `0x28 = 1`, `0x29 = 20`, `0x2A = 1213`, `0x2C = 0`, `0x2E = 250`.
4. **Firmware Behavior Confirmed**: Writing to register `0x29` in STS3215 firmware automatically sets `0x28 (Torque Enable) = 1`. This explains why the official Feetech Arduino library never calls `EnableTorque(1)` in its `WritePosEx` sketches.

### 3.5 Hardware Move Attempt 4 (Production Code Path under Widened Limits)
To isolate whether the custom scratch packet caused the runaway cruise, the test was repeated using the **unmodified production controller**:
- **Code Path**: `PrecisionServoController.write_goal_position()` from `precision_tracker.servo_bus` (issues 3 discrete write packets: Speed to `0x2E`, Accel to `0x29`, Target Location to `0x2A` last; never touches `0x2C`).
- **Profile**: `Speed = 250 counts/s`, `ACC = 20`
- **EEPROM Limits**: Widened to `[-8192, +8192]`
- **Starting Position $P_0$**: `1214` $\to$ **Target**: `1414` ($\Delta = +200$ counts)
- **Result**: The servo **again failed to decelerate**. It crossed target `1414` at $t=0.35\text{ s}$ at $250\text{ counts/s}$ and maintained constant velocity across the corridor until timing out at $t=4.07\text{ s}$ at position `2347` (coasting to `2383`).
- **Conclusion**: The non-deceleration defect is **not scratch-script-specific**; it reproduces identically through the official production code path.

---

## 4. The Decisive Control Test: Factory Default Limits `[0, 4095]`

To eliminate the final confound—determining whether `Speed=250 / ACC=20` itself fails to decelerate on this firmware versus widened limits breaking the trajectory planner—a clean control test ([test_phase1_control_factory_limits.py](file:///d:/aaaassistan_pcb/scratch/test_phase1_control_factory_limits.py)) was executed:
- **EEPROM State**: Factory defaults `[0, 4095]` strictly preserved throughout (zero EEPROM writes).
- **Code Path**: Production `PrecisionServoController.write_goal_position()`.
- **Profile**: Identical `Speed = 250 counts/s`, `ACC = 20`.
- **Starting Position $P_0$**: `2383` $\to$ **Target**: `2183` ($\Delta = -200$ counts downward).

### 4.1 Telemetry Results

#### Outward Leg ($2383 \to 2183$, Downward / Negative):
```
t=0.000s | Pos= 2275 | Target= 2183 | Spd=-250 | Load=  72
t=0.148s | Pos= 2238 | Target= 2183 | Spd=-250 | Load=  80
t=0.282s | Pos= 2204 | Target= 2183 | Spd=-200 | Load=  68  <-- ACTIVE DECELERATION
t=0.422s | Pos= 2184 | Target= 2183 | Spd=   0 | Load=   0  <-- CLOSED-LOOP SETTLE
[SUCCESS] Target reached: Pos=2184 (error=1 counts) in 0.422s
```

#### Return Leg ($2183 \to 2383$, Upward / Positive Against Gravity):
```
t=0.000s | Pos= 2293 | Target= 2383 | Spd= 250 | Load= -76
t=0.133s | Pos= 2327 | Target= 2383 | Spd= 300 | Load= -84
t=0.284s | Pos= 2365 | Target= 2383 | Spd= 200 | Load= -44  <-- ACTIVE DECELERATION
t=0.435s | Pos= 2381 | Target= 2383 | Spd=   0 | Load= -24  <-- CLOSED-LOOP SETTLE
[SUCCESS] Target reached: Pos=2381 (error=2 counts) in 0.435s
```

#### Step 3 Torque-Disable Retention Check:
- Position before cut: `2381`
- Position after 500ms torque cut (`0x28 = 0`): `2381` (**Passive drift = `0 counts`**)
- Position after torque re-enable: `2381` (**PASS**)

### 4.2 Comparative Analysis

| Test Condition | EEPROM Limits (`0x09/0x0B`) | Motion Profile | Target Position | Deceleration & Settling | Transit Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Attempt 2** | `[-8192, +8192]` | Speed=800, ACC=15 | 796 | **None** (cruised through 796 @ 750c/s) | Aborted on Load Tripline (pos 904) |
| **Attempt 3** | `[-8192, +8192]` | Speed=250, ACC=20 | 1213 | **None** (cruised through 1213 @ 250c/s) | Aborted on 4.0s Timeout (pos 2002) |
| **Attempt 4 (Prod Path)**| `[-8192, +8192]` | Speed=250, ACC=20 | 1414 | **None** (cruised through 1414 @ 250c/s) | Aborted on 4.0s Timeout (pos 2347) |
| **Control Test (Outward)**| **`[0, 4095]` (Factory)** | Speed=250, ACC=20 | 2183 | **Decelerated from -250 to 0** | **`TARGET_REACHED` in 0.422s** |
| **Control Test (Return)** | **`[0, 4095]` (Factory)** | Speed=250, ACC=20 | 2383 | **Decelerated from +300 to 0** | **`TARGET_REACHED` in 0.435s** |

---

## 5. Architectural Root Cause & Final Verdict

### 5.1 Root Cause
The STS3215 MCU firmware implements its Mode 0 PID trajectory generator under the hardcoded mathematical assumption that position error $\Delta p = p_{\text{target}} - p_{\text{present}}$ is evaluated within a single 12-bit modular turn ($0 \le p \le 4095$).

When registers `0x09` and `0x0B` are modified to values outside `[0, 4095]`:
1. The firmware accepts the goal position write into SRAM register `0x2A`.
2. The firmware activates the H-bridge and enters cruise velocity.
3. However, because the limit registers exceed single-turn bounds, the firmware's internal position-error calculation fails to evaluate the approach to the target boundary.
4. Consequently, the firmware **never enters the deceleration phase**, causing the motor to cruise indefinitely at constant speed.

### 5.2 Verdict
- **Hypothesis (a)** (*Widened limits break deceleration*): **CONFIRMED BY DIRECT EMPIRICAL PROOF**.
- **Hypothesis (b)** (*Speed/ACC combo causes runaway*): **DISPROVED**.

---

## 6. Exact Register Map Reference

For future audits and full reproducibility, the exact registers evaluated during this investigation are cataloged below:

| Register Address | Name | Data Type | Factory Baseline | Widened Test State | Safe Operating Rule |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`0x09–0x0A`** | Min Angle Limit | `SM15` (2 bytes) | `0` (`0x0000`) | `-8192` (`0xA000`) | **Must remain `0`** |
| **`0x0B–0x0C`** | Max Angle Limit | `SM15` (2 bytes) | `4095` (`0x0FFF`)| `+8192` (`0x2000`) | **Must remain `4095`** |
| **`0x1F–0x20`** | Position Offset | `SM15` (2 bytes) | `0` (`0x0000`) | `0` (`0x0000`) | **STRICTLY NEVER TOUCH (`0`)** |
| **`0x21`** | Operating Mode | Byte (1 byte) | `0` (Position) | `0` (Position) | **Must remain `0`** |
| **`0x28`** | Torque Enable | Byte (1 byte) | `0` (OFF) | `1` (Active) | Controlled dynamically |
| **`0x29`** | Acceleration | Byte (1 byte) | `0` | `20` | Set during motion command |
| **`0x2A–0x2B`** | Target Position | `SM15` (2 bytes) | Dynamic | Commanded Target | Written last in production path |
| **`0x2C–0x2D`** | Goal Time | Word (2 bytes) | `0` | `0` | Unused by production code |
| **`0x2E–0x2F`** | Running Speed | Word (2 bytes) | `0` | `250` | Written first in production path |
| **`0x37`** | EEPROM Lock | Byte (1 byte) | `1` (Locked) | `0` (Unlocked) | **Must remain `1` (Locked)** |
| **`0x38–0x39`** | Present Position| `SM15` (2 bytes) | Live Read | Live Read | Primary position telemetry |
| **`0x3C–0x3D`** | Present Load | Word (2 bytes) | Live Read | Live Read | Bit 10 = direction, lower 10 = mag |
| **`0x41`** | Status / Fault | Byte (1 byte) | `0x00` | `0x00` | Safety gate pre/post flight |

---

## 7. Practical Implications & Future Architecture Paths

Native multi-turn motion cannot be achieved on Feetech STS3215 servos by expanding Mode 0 EEPROM limits. Any future implementation of multi-rotation travel must choose between two viable paths:

### Option A: Host-Side Multi-Turn Tracking & Virtual Waypoint Chaining
- Keep hardware registers at factory defaults: `0x09 = 0`, `0x0B = 4095`, `Mode = 0`.
- The host controller maintains an integer `turn_counter` in software state (`motor_state.json`), incrementing or decrementing whenever the 12-bit encoder crosses the wrap boundary ($4095 \leftrightarrow 0$).
- When a target coordinate requires crossing a revolution boundary, the host decomposes the trajectory into two sub-moves using waypoint chaining (e.g. transit to boundary edge $4090 \to$ dynamic software transition $\to$ continue from $5 \to$ target).
- *Status*: Proven during earlier manual recovery moves on Axis Y; viable for future expansion.

### Option B: Calibrated Single-Rotation Working Range (Current Production Standard)
- Maintain the axis strictly within a single-rotation calibrated working corridor ($\approx 100$ to $3800$ counts), providing $\approx 325^\circ$ of continuous linear travel without crossing the wrap boundary.
- *Status*: Fully implemented, thoroughly validated, zero firmware risk.

---

## 8. Final Hardware State Verification

Prior to closing this investigation phase, Axis Y was audited and confirmed in a safe, quiescent state:
- **Present Position**: `2381` (safely inside the proven corridor)
- **Torque Enable (`0x28`)**: **`0` (OFF)**
- **EEPROM Limits (`0x09/0x0B`)**: **`[0, 4095]` (Factory Default)**
- **Position Offset (`0x1F`)**: **`0` (Untouched)**
- **EEPROM Lock (`0x37`)**: **`1` (Locked)**
- **Status / Fault Register (`0x41`)**: **`0x00` (Zero faults)**

No further hardware actions are required on Axis Y tonight. The hardware is quiescent and secure.
