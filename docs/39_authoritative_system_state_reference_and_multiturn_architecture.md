# REPORT 39: AUTHORITATIVE SYSTEM STATE REFERENCE & MULTI-TURN ARCHITECTURE

**Date**: October 4, 2026  
**Status**: ACTIVE AUTHORITATIVE SSOT REFERENCE  
**Classification**: Permanent System Reference & Engineering Architecture  
**Hardware Interface**: Feetech STS3215 TTL Bus Servos on `COM3` @ 1,000,000 baud  
**Primary Archive Target**: `D:\aaa_new_microscope\reports\39_authoritative_system_state_reference_and_multiturn_architecture.md`  
**Redundant Workspace Copy**: `d:\aaaassistan_pcb\docs\39_authoritative_system_state_reference_and_multiturn_architecture.md`  

---

## EXECUTIVE SUMMARY

This document serves as the single, authoritative, cold-readable technical reference for the 3-axis Feetech STS3215 servo-driven digital pathology microscope stage. It documents:
1. The **exact live hardware state** independently queried from physical hardware registers on October 4, 2026.
2. The **chronological operational history** spanning the initial crash, axis midpoint calibrations, production hardening, and whole-slide scanning milestones.
3. The **findings of the multi-turn / Mode 3 hardware investigation** that permanently banned EEPROM limit manipulation.
4. The **unambiguous distinction** between what is fully operational in production today versus what is designed-only (zero code written).
5. A comprehensive **File Map** defining every active, state, and documentation artifact across the system.
6. The approved **phased execution roadmap** for implementing dual-range multi-turn operation.

Any engineer or agent reading this document months or years from now can reconstruct the exact technical state of the stage without re-deriving or re-investigating any prior findings.

---

## 1. SYSTEM OVERVIEW (CURRENT AS OF OCTOBER 4, 2026)

### 1.1 Actuation and Control Architecture
The microscope stage consists of three orthogonal axes driven by Feetech STS3215 high-torque serial bus smart servos communicating over a half-duplex TTL serial bus on `COM3` at 1,000,000 baud (8-N-1):
- **Axis X (Horizontal Raster)**: Servo ID 5
- **Axis Y (Vertical Step)**: Servo ID 3
- **Axis Z (Optical Focus)**: Servo ID 4

All three servos operate strictly in **Mode 0 (Position Control Mode)** with factory EEPROM angle limits hard-locked at $[0, 4095]$ ($0^\circ \text{ to } 360^\circ$, 12-bit absolute magnetic encoder resolution). Continuous multi-turn stage positioning is tracked by host software unwrapping the single-turn encoder stream into continuous signed 32-bit total counts ($\text{total\_counts} = \text{rotations} \times 4096 + \text{raw}$).

### 1.2 Fresh Live Hardware Telemetry
*Independently queried via direct serial register read instruction (0x02) on October 4, 2026 at 01:34:03:*

| Parameter | Register Address | Axis X (ID 5) | Axis Y (ID 3) | Axis Z (ID 4) | Engineering Unit / Interpretation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Present Position** | `0x38` (2B) | **331** | **3260** | **1958** | Raw counts $[0..4095]$ ($29.09^\circ$, $286.52^\circ$, $172.09^\circ$) |
| **Torque Enable** | `0x28` (1B) | **0** | **0** | **0** | Disabled (Stage is safe, freewheeling, zero power dissipation) |
| **Operating Mode** | `0x21` (1B) | **0** | **0** | **0** | Mode 0 (Position Control Mode) |
| **EEPROM Lock** | `0x37` (1B) | **1** | **1** | **1** | Locked (EEPROM protected against accidental writes) |
| **Position Offset** | `0x1F` (2B) | **0** (`0x0000`) | **0** (`0x0000`) | **0** (`0x0000`) | Factory zero offset active across all axes |
| **Min Angle Limit** | `0x09` (2B) | **0** (`0x0000`) | **0** (`0x0000`) | **0** (`0x0000`) | Factory default hard limit ($0^\circ$) |
| **Max Angle Limit** | `0x0B` (2B) | **4095** (`0x0FFF`) | **4095** (`0x0FFF`) | **4095** (`0x0FFF`) | Factory default hard limit ($360^\circ$) |
| **Present Load** | `0x3C` (2B) | **0** | **0** | **0** | Zero external load detected |
| **Present Current** | `0x45` (2B) | **0** | **0** | **0** | 0.0 mA current draw |
| **Present Voltage** | `0x3E` (1B) | **74** (7.4V) | **73** (7.3V) | **73** (7.3V) | Nominal 2S LiPo / 7.4V regulated bus supply |
| **Hardware Status** | `0x41` (1B) | **0x00** | **0x00** | **0x00** | Clean (Zero over-voltage, temperature, or stall flags) |

### 1.3 Verified Corridor State on Disk (`motor_limits.json` / `motor_limits.verified.json`)
The active Single Source of Truth (SSOT) configuration files on disk currently contain:

```json
{
  "Z": {
    "limit_type": "hard_mechanical",
    "margin_counts": 2,
    "min_limit": {
      "servo_id": 4,
      "counts": 1959,
      "single_deg": 172.18,
      "rotations": 0,
      "total_deg": 172.18,
      "recorded_at": "2026-10-04 01:19:24"
    },
    "max_limit": {
      "servo_id": 4,
      "counts": 1976,
      "single_deg": 173.67,
      "rotations": 0,
      "total_deg": 173.67,
      "recorded_at": "2026-10-04 01:18:12"
    }
  },
  "Y": {
    "limit_type": "soft_optical",
    "margin_counts": 60,
    "min_limit": {
      "servo_id": 3,
      "counts": 1532,
      "single_deg": 134.65,
      "rotations": 0,
      "total_deg": 134.65,
      "recorded_at": "2026-10-04 01:18:50"
    },
    "max_limit": {
      "servo_id": 3,
      "counts": 3260,
      "single_deg": 286.52,
      "rotations": 0,
      "total_deg": 286.52,
      "recorded_at": "2026-10-04 01:19:40"
    }
  },
  "X": {
    "limit_type": "soft_optical",
    "margin_counts": 60,
    "min_limit": {
      "servo_id": 5,
      "counts": 2327,
      "single_deg": 204.52,
      "rotations": 0,
      "total_deg": 204.52,
      "recorded_at": "2026-10-04 01:18:43"
    },
    "max_limit": null
  }
}
```

#### Detailed Corridor Analysis:
- **Axis Z (Optical Focus)**:
  - Physical limits: $[1959, 1976]$ (Span: 17 counts $\approx 1.49^\circ$).
  - Safety margin: 2 counts. Safe corridor: $[1961, 1974]$.
  - Status: Fully enclosed within single rotation (Rot 0), verified hard mechanical stops.
- **Axis Y (Vertical Step)**:
  - Physical limits: $[1532, 3260]$ (Span: 1728 counts $\approx 151.87^\circ$).
  - Safety margin: 60 counts. Safe corridor: $[1592, 3200]$.
  - Status: Fully enclosed within single rotation (Rot 0), verified soft optical travel.
- **Axis X (Horizontal Raster)**:
  - Physical limits: `min_limit` recorded at 2327 counts (Rot 0). `max_limit` is currently **UNSET on disk**.
  - Root cause of unset `max_limit`: The operator jogged Axis X to its true physical maximum travel at raw count 331 in Rotation 1 (total count 4427). When attempting to record this limit using `movements.py`, the system's rotation validation guard triggered:
    ```text
    [RECORD BLOCKED] This recording would create a wrap-spanning corridor!
    MIN endpoint: Rot 0, raw=2327 (total=2327)
    MAX endpoint: Rot 1, raw=331 (total=4427)
    Endpoints are in DIFFERENT rotations.
    ```
    This block functioned exactly as designed to protect hardware from a wrap-spanning Mode 0 motion crash, leaving X `max_limit` pending the implementation of the dual-range architecture.
- **Historical Production Whole-Slide Scan Baseline**:
  Prior to the October 4 recalibration, the production whole-slide scanning suite operated within the verified single-rotation corridors:
  - X: $[5850..7518]$ (Span: 1668 counts, Safe: $[5910..7458]$)
  - Y: $[1589..3720]$ (Span: 2131 counts, Safe: $[1649..3660]$)
  - Z: $[-1887..-1827]$ (Span: 60 counts, Safe: $[-1885..-1829]$)

### 1.4 Operational Safety Matrix (What Is Safe vs. What Is Not Available)
- **Currently SAFE to do**:
  1. Manual interactive jogging via `movements.py` within single-rotation bounds (the active rotation guard blocks any cross-boundary move).
  2. High-precision autofocus sweeps and live camera streaming.
  3. 2D automated raster scanning via `triple_scan_suite_runner.py` *only after restoring/recording an enclosed single-rotation corridor for Axis X*.
- **Currently NOT AVAILABLE / UNSAFE**:
  1. Multi-turn stage travel (`operation_range`): The multi-turn architecture is **designed only; zero code has been written**. Traversing across the 4095/0 boundary in Mode 0 without the automated transition pulse will cause an immediate reverse runaway crash.
  2. Automated boundary crossing: Not implemented in controller or runner.
  3. Recording multi-turn corridors in `movements.py`: Blocked by current single-rotation validation.

---

## 2. CHRONOLOGICAL HISTORY: HOW THE SYSTEM GOT HERE

The current system state is the outcome of rigorous forensic investigations, hardware validation, and systematic defect elimination. The key milestones and their authoritative source documents are summarized below:

```
+----------------------------------------------------------------------------------------------------+
|                                    HISTORICAL CHRONOLOGY                                           |
+----------------------------------------------------------------------------------------------------+
| 1. Mode 0 Wrap Crash               --> Root Cause: PID Error Evaluated Linearly in [0, 4095]      |
|    (Report 33, 34, 38)                 Waypoints crossing 4095/0 trigger -4095 count reverse runaway|
+----------------------------------------------------------------------------------------------------+
| 2. Production Hardening Suite      --> Replaced silent "or 0" with _read_location_strict()         |
|    (Reports 30, 32, 38)                Fixed unimported autofocus engine & sys.path collision       |
|                                        Added movements.py rotation-validation recording gate       |
+----------------------------------------------------------------------------------------------------+
| 3. Axis X Midpoint Calibration     --> Re-centered physical travel into single rotation            |
|    (Reports 35, 36)                    Midpoint offset calibrated at 2327 counts                   |
+----------------------------------------------------------------------------------------------------+
| 4. Axis Y Midpoint Calibration     --> Attempt 1 failed (calc error), Attempt 2 succeeded          |
|    (Report 38)                         Y-axis corridor centered in Rot 0: [1532..3260]              |
+----------------------------------------------------------------------------------------------------+
| 5. Whole-Slide 4K Scan Milestone   --> 308 tiles (14x22), zero crashes, crisp focus,              |
|    (Reports 10, 13, 23, 32)            validated optical symmetry (R_blur approx 1.00)             |
+----------------------------------------------------------------------------------------------------+
| 6. Multi-Turn / Mode 3 Forensics   --> Mode 3 ruled out (relative step only, no absolute pos)     |
|    (Findings Doc, Design Doc)          EEPROM limit widening proved broken by direct hardware test |
|                                        Dual-range architecture designed and formally approved       |
+----------------------------------------------------------------------------------------------------+
```

### 2.1 The GoalDirectionMismatchError Crash and Mode 0 Non-Wrapping Mechanics
- **Event**: During early motion testing across large spans, motion commands intermittently triggered catastrophic unbraked motion into mechanical endstops, throwing `GoalDirectionMismatchError`.
- **Root Cause Analysis**: The Feetech STS3215 firmware operates in Mode 0 (Position Control Mode) by evaluating the position error linearly within the absolute $[0, 4095]$ register space:
  $$\text{Error} = \text{Goal}_{\text{raw}} - \text{Present}_{\text{raw}}$$
  The firmware contains **zero circular wrap logic**. If an axis is at raw position 4090 and receives a command to move forward to raw position 10 (intended $\Delta = +16$ counts across the boundary), the servo firmware calculates:
  $$\text{Error} = 10 - 4090 = -4080 \text{ counts}$$
  Instead of advancing $+16$ counts, the servo commands maximum reverse torque at full acceleration to travel $-4080$ counts backward, violently slamming into the opposite endstop.
- **Reference Reports**:
  - `D:\aaa_new_microscope\reports\33_z_axis_range_investigation_and_endstop_jamming_root_cause_report.md`
  - `D:\aaa_new_microscope\reports\34_corridor_recalibration_sweep_direction_and_backlash_compensation_report.md`
  - `D:\aaa_new_microscope\reports\38_axis_recalibration_and_motion_recovery_investigation_report.md`

### 2.2 Production Codebase Hardening Suite
To transform experimental scripts into a robust scientific production platform, four major architectural vulnerabilities were identified and hardened:
1. **The Silent `or 0` Fallback Vulnerability**:
   - *Flaw*: Early versions of `servo_bus.py` used `read_present_position() or 0`. If a serial packet experienced a transient checksum error or collision, the function silently returned 0. The motion controller interpreted 0 as a genuine physical position at the far end of the axis, triggering an emergency reverse runaway.
   - *Fix*: Implemented `_read_location_strict()` in `precision_tracker/servo_bus.py`. Transient read failures are retried 3 times with 20ms delays; if communication fails, it raises `HardwareCommunicationError` rather than returning a corrupt synthetic coordinate.
2. **Missing Autofocus Call-Site Alignment**:
   - *Flaw*: `triple_scan_suite_runner.py` previously called an unimported placeholder `sweep_optical_focus` with mismatched arguments (settle 0.35s, step 3, 1080p), while `autofocus.py` maintained the true 4K pipeline.
   - *Fix*: Unified the runner with canonical `run_autofocus_sweep()` from `autofocus.py` (settle 1.5s, step 1, 4K native, 25-count upward backlash overshoot compensation).
3. **`sys.path` Collision and Shadowing Fix**:
   - *Flaw*: An external path `r"D:\smart_scan\SmartCytoScan"` was prepended to `combined_scan.py`, accidentally shadowing local microscope drivers with incompatible legacy code.
   - *Fix*: Removed external paths and placed an immutable `sys.path.insert(0, microscope_root)` guard at the head of all production runners.
4. **`movements.py` Rotation-Validation Guard**:
   - *Flaw*: Operators could accidentally record a corridor spanning two rotations, baking a Mode 0 wrap-crash into `motor_limits.json`.
   - *Fix*: Added a strict validation gate during the `[R]` recording flow. If `rot_min != rot_max`, saving is aborted with a prominent diagnostic warning.
- **Reference Reports**:
  - `D:\aaa_new_microscope\reports\30_comprehensive_system_architecture_and_codebase_updates_report.md`
  - `D:\aaa_new_microscope\reports\32_triple_scan_suite_architecture_and_production_benchmark_report.md`
  - `D:\aaa_new_microscope\reports\FUTURE_WORK_AND_KNOWN_ISSUES.md`

### 2.3 Physical Axis Midpoint Calibrations
Because stage travel exceeded single-turn space or crossed the $4095/0$ boundary in default mechanical mounting, physical midpoint calibrations were executed:
- **Axis X Midpoint Calibration**:
  - Physical stage was centered mechanically and electronic zero re-referenced.
  - Documented in `D:\aaa_new_microscope\reports\35_x_axis_midpoint_calibration_execution_and_rollback_report.md` and `36_x_axis_system_rebaseline_and_corridor_realignment_report.md`.
- **Axis Y Midpoint Calibration**:
  - Executed on October 1, 2026. First attempt had an arithmetic transposition error in the target midpoint calculation; second attempt succeeded completely, placing the entire optical scanning range $[1532..3260]$ safely inside Rotation 0 ($134.65^\circ \text{ to } 286.52^\circ$).
  - Documented in `D:\aaa_new_microscope\reports\38_axis_recalibration_and_motion_recovery_investigation_report.md`.

### 2.4 Whole-Slide Scanning Production Milestone
The hardened production architecture achieved complete, unattended scientific whole-slide scanning:
- Complete acquisition of **308 tiles** ($14 \text{ rows} \times 22 \text{ columns}$) at native 4K UHD resolution.
- Zero motion crashes, zero lost frames, zero communication dropouts.
- Optical sharpness symmetry validated at $R_{\text{blur}} \approx 1.00$, confirming zero vibration blur or directional backlash degradation.
- Documented in `D:\aaa_new_microscope\reports\10_whole_slide_sharp_scan_deep_evaluation_report.md`, `13_calibrated_whole_slide_mosaic_stitching_report.md`, and `23_scientific_4k_gigapixel_ome_tiff_report.md`.

---

## 3. MULTI-TURN / MODE 3 HARDWARE INVESTIGATION

### 3.1 Motivation
While single-rotation corridors ($<4096$ counts) successfully support full slide scans within bounded regions, the physical stage mechanisms for X and Y possess mechanical travel that spans multiple complete rotations of the servo horn. The operator requested an architecture enabling multi-turn stage travel without sacrificing Mode 0 position holding or risking wrap-around runaway.

### 3.2 Mode 3 (Step / Multi-Turn Mode) Ruled Out
- **Investigation**: Tested Mode 3 (`REG_OPERATING_MODE = 3`) to determine if the STS3215 supports native multi-turn absolute positioning.
- **Hardware Finding**: In Mode 3, register `0x2A` (`Goal Position`) ceases to function as an absolute spatial coordinate. Instead, it acts as an **incremental step accumulator** relative to the current position.
- **Verdict**: Ruled out. Absolute positional repeatability, hardware-enforced boundaries, and deterministic recovery after power loss are impossible under incremental step control.
- **Reference**: `d:\aaaassistan_pcb\docs\MULTI_TURN_MODE0_INVESTIGATION_FINDINGS.md` (SHA-256: `afbdef2aa94393c7403b3f4453f36ee1ae90643f32a54bd4cbcb06f2d0538f27`).

### 3.3 EEPROM Angle Limit Widening Ruled Out and Permanently Banned
- **Hypothesis**: Could registers `0x09` (`Min Angle Limit`) and `0x0B` (`Max Angle Limit`) be set beyond factory defaults (e.g. $[0, 8191]$) to allow Mode 0 to span multiple rotations natively?
- **Direct Hardware Proof**: On live hardware, setting `0x0B` to 8191 corrupts internal firmware position tracking:
  1. Position reads in `0x38` jump erratically upon passing 4095.
  2. Mode 0 position commands beyond 4095 cause unpredictable motor oscillations and stalls.
- **Architectural Invariant**:
  > **PERMANENT SYSTEM RULE**: Registers `0x09` and `0x0B` must remain strictly at their factory default values ($0$ and $4095$). Any script proposing to modify these registers for range extension is fundamentally unsafe and strictly prohibited.

### 3.4 The Dual-Range Software Architecture (Designed, Not Yet Implemented)
To solve the multi-turn requirement while keeping hardware locked in factory Mode 0, a dual-range software architecture was conceived, detailed in `d:\aaaassistan_pcb\docs\MULTI_TURN_MODE0_SOFTWARE_DESIGN.md`:
1. **`scan_range` (Single-Rotation Safe Zone)**:
   - Dedicated strictly to automated 2D raster scanning.
   - Strictly enforced $\text{rot\_min} == \text{rot\_max}$ (zero boundary crossings).
   - Operates purely in Mode 0 with zero mode switching and zero EEPROM writes.
   - Enforced by `verify_corridor_ssot.py` and consumed by `triple_scan_suite_runner.py`.
2. **`operation_range` (Full Physical Mechanical Travel)**:
   - Covers the entire mechanical stroke of the stage, including multi-turn spans.
   - Permitted only for gross repositioning, specimen exchange, and homing.
   - Crosses boundaries using an automated **Mode 1 velocity creep transition pulse**:
     - Servo approaches boundary in Mode 0.
     - Within $[10, 50]$ counts of boundary, controller unlocks EEPROM, switches to Mode 1 (Speed Control Mode).
     - Issues a slow velocity pulse ($50 \text{ counts/s}$) across the $4095/0$ boundary.
     - Host unwrapper increments/decrements rotation counter upon crossing.
     - Controller pre-aligns goal register `0x2A` to live `0x38`, switches back to Mode 0, locks EEPROM, and resumes position control.
3. **EEPROM Endurance Analysis**:
   - Switching operating mode (`0x21`) requires unlocking and writing EEPROM, consuming 2 write cycles per boundary crossing.
   - Because STS3215 EEPROM has an endurance of $10,000 \text{ to } 100,000$ write cycles, **boundary crossings are strictly forbidden during automated scanning**. They are reserved exclusively for occasional gross stage positioning.

---

## 4. WHAT IS IMPLEMENTED VS. WHAT IS DESIGNED-ONLY

To eliminate any ambiguity between active production software and proposed designs, the system status is categorized below:

| Subsystem / Feature | Current Status | Operating Details |
| :--- | :---: | :--- |
| **Mode 0 Absolute Position Control** | **PRODUCTION** | Live on COM3. Hard-locked at factory $[0, 4095]$ limits. |
| **Single-Rotation Corridor Protection** | **PRODUCTION** | Active in `movements.py` and `triple_scan_suite_runner.py`. Blocks wrap saves. |
| **Strict Serial Read (`_read_location_strict`)** | **PRODUCTION** | 3 retries, raises `HardwareCommunicationError`. Zero `or 0` in production path. |
| **Unified 4K Autofocus Engine** | **PRODUCTION** | 1.5s dwell, step=1, 25-count backlash overshoot compensation. |
| **Dual-Range Schema (`v2.0.0`)** | **DESIGNED-ONLY** | Schema drafted in Design Doc Section 7. **Zero code written; not on disk.** |
| **Migration Script (`migrate_corridor_to_dual_range.py`)** | **DESIGNED-ONLY** | Specifications defined. File does not exist yet. |
| **`movements.py` Dual-Range Recording Flow** | **DESIGNED-ONLY** | Interactive `[R]` menu for selecting range type is not yet implemented. |
| **Linear Hardware Direction Guard** | **DESIGNED-ONLY** | Algorithm designed to replace modulo-2048 guard in `controller.py`. Not implemented. |
| **Mode 1 Automated Boundary Transition Hand-Off** | **DESIGNED-ONLY** | Velocity creep pulse across 4095/0 is designed; Phase 1a scratch test not yet run. |
| **Real `operation_range` Limits on Disk** | **DESIGNED-ONLY** | Stage physical limits not recorded; awaiting migration and recording flow. |

### 4.1 Documented Technical Debt and Known Issues (from `FUTURE_WORK_AND_KNOWN_ISSUES.md`)
1. **Silent Exception Suppression via `os._exit(0)`**:
   - In `triple_scan_suite_runner.py`, the global `finally:` block executes `os._exit(0)`. If an unexpected exception occurs (e.g. transient serial timeout or direction fault), Python terminates immediately at the C-runtime level without printing the traceback to `sys.stderr`, masking root-cause diagnostics.
   - *Status*: Documented; pending replacement with proper exception logging and `sys.exit()`.
2. **Asynchronous Signal Race Condition (SIGINT vs. `os._exit(0)`)**:
   - Pressing Ctrl+C during active motion triggers `finally: os._exit(0)`, cutting communication before the servo holding position is verified, risking unbraked coasting under cable tension.
   - *Status*: Documented; requires explicit signal handler freezing motion with active holding torque before exit.
3. **Four Manual Diagnostic Scripts Retaining `or 0`**:
   - `calibrate_endstops_step_by_step.py`, `quick_test_min_dwell_max.py`, `sweep_limits.py`, and `tools/return_stage_to_corridor_center.py` still contain `or 0` fallback patterns.
   - *Status*: Low risk (non-production diagnostic tools), pending refactor.
4. **Non-Atomic Multi-File Rebaseline Risk**:
   - Updating limits across multiple files without two-phase commit risks transient Windows file locking conflicts.
   - *Status*: Documented; two-phase transactional commit utility recommended.

---

## 5. SYSTEM FILE MAP

### 5.1 Production Code (`D:\aaa_new_microscope\`)
- `triple_scan_suite_runner.py`: Primary production scanning orchestrator. Runs continuous, settle-and-shoot, and step-AF scans with SSOT corridor validation.
- `movements.py`: Primary interactive operator console. Provides manual axis jogging, position display, speed configuration, and corridor recording.
- `autofocus.py`: Canonical 4K autofocus engine implementing predictive search, contrast evaluation, and backlash overshoot compensation.
- `precision_tracker/servo_bus.py`: Core serial communication layer. Implements strict packet framing, checksum verification, retry logic, and register read/write.
- `precision_tracker/controller.py`: High-level motion controller. Translates user coordinates into multi-turn unwrapped trajectories with directional safety guards.
- `precision_tracker/position_tracker.py`: Real-time position tracking engine maintaining unwrapped multi-turn total counts.
- `verify_corridor_ssot.py`: Pre-flight verification utility confirming runtime parameters match disk SSOT configurations.

### 5.2 Single Source of Truth (SSOT) Configuration & State Files
- `D:\aaa_new_microscope\motor_limits.json`: Active authoritative runtime corridor configuration. Defines physical limits, margins, and safe bounds for X, Y, Z.
- `D:\aaa_new_microscope\motor_limits.verified.json`: Verified baseline copy of corridor limits. Used for integrity comparisons and pre-flight audits.
- `D:\aaa_new_microscope\motor_state.json`: Actuator operational state cache (present positions, holding torque status, homing timestamps).
- `d:\aaaassistan_pcb\motor_state.json`: Synchronized secondary workspace state cache.

### 5.3 Active Architectural & Investigation Reports
- `d:\aaaassistan_pcb\docs\MULTI_TURN_MODE0_INVESTIGATION_FINDINGS.md`: Authoritative findings document establishing Mode 3 failure, EEPROM limit widening failure, and the permanent ban on registers 0x09/0x0B modification.
- `d:\aaaassistan_pcb\docs\MULTI_TURN_MODE0_SOFTWARE_DESIGN.md`: Approved Phase 0 engineering specification for dual-range architecture, Mode 1 transition pulse, and enclosure validation.
- `D:\aaa_new_microscope\reports\38_axis_recalibration_and_motion_recovery_investigation_report.md`: Forensic report detailing Y-axis midpoint recalibration and motion recovery.
- `D:\aaa_new_microscope\reports\36_x_axis_system_rebaseline_and_corridor_realignment_report.md`: Technical record of X-axis midpoint recentering and corridor rebaselining.
- `D:\aaa_new_microscope\reports\FUTURE_WORK_AND_KNOWN_ISSUES.md`: Living ledger of architectural technical debt, known edge-cases, and planned hardening items.
- `D:\aaa_new_microscope\reports\39_authoritative_system_state_reference_and_multiturn_architecture.md`: **This document**. Single authoritative system overview.

---

## 6. SEQUENTIAL NEXT STEPS ROADMAP

In accordance with established system engineering protocol, multi-turn implementation proceeds strictly in sequential phases. No production code is modified, no files are deleted, and no boundary-crossing motion is executed until prior phases are formally validated:

```
[PHASE 0: COMPLETED]
  |-- Investigation Findings Document (MULTI_TURN_MODE0_INVESTIGATION_FINDINGS.md)
  |-- Dual-Range Architecture Design (MULTI_TURN_MODE0_SOFTWARE_DESIGN.md)
  \-- Authoritative System State Reference (REPORT 39)
        |
        v
[PHASE 1: DUAL-RANGE CONFIGURATION & VALIDATION GATES]
  |-- Step 1: Build and dry-run 'migrate_corridor_to_dual_range.py' (Upgrades schema to v2.0.0)
  |-- Step 2: Implement dual-range recording flow & enclosure gates in 'movements.py'
  \-- Step 3: Implement corrected linear hardware direction guard in 'controller.py'
        |
        v
[PHASE 2: ISOLATED HARDWARE PROOF-OF-CONCEPT (PHASE 1a)]
  |-- Step 4: Author isolated test script 'scratch/test_phase1a_boundary_transition.py'
  |-- Step 5: Execute controlled Mode 1 creep pulse across 4095/0 on Axis Y under manual supervision
  \-- Step 6: Verify zero stall, zero runaway, and seamless position unwrapper coherence
        |
        v
[PHASE 3: PHYSICAL CORRIDOR RECORDING & FINAL PRODUCTION COMMISSIONING]
  |-- Step 7: Record true physical mechanical travel into 'operation_range' via movements.py
  |-- Step 8: Validate that 'scan_range' remains strictly single-rotation and fully enclosed
  \-- Step 9: Execute full system health audit and archive obsolete investigation scripts
```

### Immediate Action Item
Upon review and approval of this Report 39, proceed directly to **Phase 1, Step 1**: authoring and testing the non-destructive schema migration utility `migrate_corridor_to_dual_range.py`.

---
*Report 39 Certified Complete & Authoritative — October 4, 2026.*
