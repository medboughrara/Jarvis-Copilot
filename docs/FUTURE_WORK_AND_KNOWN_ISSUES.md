# Future Improvements & Known Technical Debt

**Date**: September 28, 2026 (Updated from September 24, 2026)  
**Repository**: `D:\aaa_new_microscope`  
**Purpose**: Standalone reference of resolved engineering milestones, permanent open architectural items, and structural technical debt.

---

### 1. [RESOLVED] Axis Y Midpoint Calibration & Second Calibration (-932 Shift)
- **Previous Status**: Axis Y recovery move completed at raw 2966, calibration pending.
- **Resolution & Evolution**:
  1. **Phase 1B & 1C**: Executed in-place EEPROM midpoint calibration on Servo ID 3 (`0x28 = 128`), resetting offset to mechanical center $\approx 2048$, and synchronized all 5 SSOT JSON files.
  2. **Second Calibration & -932 Shift**: Following physical verification of the specimen slide placement at the bottom-left of the stage, Axis Y was recalibrated from an interim $[1974, 4211]$ corridor (which approached the upper turn boundary) with an intentional **$-932\text{ counts}$ shift** to:
     $$\text{Corridor: } [1604, 3119]\text{ total counts (Rotation 0, span 1515 counts)}$$
  3. **Total Removal of Artificial Clamps**: An interim `min(4090, ...)` clamp introduced during testing was audited and completely removed from all three scan routines (`run_scan_cont_4k`, `run_scan_step_30pct`, `run_scan_step_50pct_af`). All corridors now strictly derive `y_max_safe = limits["y"][1] - margin_y` from the single source of truth.
  4. **Status**: **RESOLVED & VERIFIED IN PRODUCTION**.

---

### 2. [PERMANENT OPEN ITEM] Mode 0 GoalDirectionMismatchError Guard Blind Spot on Wrap Boundary Crossings
- **Severity**: Architectural / Latent Risk (Zero impact in current single-rotation operation; High impact if future mechanical reconfiguration crosses a 4096 wrap boundary).
- **Technical Context**:
  The Feetech STS3215 smart actuator in Closed-Loop Position Mode (Mode 0) evaluates register `0x2A` (Goal Position) relative to register `0x38` (Present Position) modulo 4096, taking the shortest angular arc ($\le 2048$ counts):
  $$\Delta_{\text{servo}} = (\text{goal\_raw} - \text{cur\_raw}) \pmod{4096} \quad (\text{mapped to } [-2047, 2048])$$
- **The Blind Spot / Guard Failure Mechanism**:
  The software controller implements a safety interlock (`GoalDirectionMismatchError`) that checks whether the sign of the commanded linear stage displacement matches the direction of the servo's live Mode 0 position error:
  $$\text{sign}(\Delta_{\text{total}}) \stackrel{?}{=} \text{sign}(\Delta_{\text{servo}})$$
  When an axis travel corridor crosses a 4096 wrap boundary (e.g. transitioning from raw 4090 to raw 0010 in a $+1$ direction):
  1. The linear stage displacement $\Delta_{\text{total}}$ is positive ($+30$ counts).
  2. The raw goal is 10, present raw is 4090. If the shortest-arc calculation or raw subtraction is evaluated without unwrapping, $\text{cur\_raw} \to \text{goal\_raw}$ can appear negative or invert direction.
  3. Conversely, if a command spans $>2048$ counts, the internal servo firmware reverses direction to take the short arc, conflicting directly with the linear stage's intended motion.
  4. The current guard either triggers a false-positive `GoalDirectionMismatchError` abort (as occurred in the original X-axis crash in Section 1 of Report 38), or, if bypassed, permits a reverse runaway.
- **Why It Cannot Bite Today**:
  Both active axes have been intentionally calibrated to reside strictly within single-rotation envelopes:
  - Axis X: $[5749, 7860]$ total counts (Turn $+1$, raw counts $[1653, 3764]$, distance to 4096 wrap $= 332$ counts).
  - Axis Y: $[1604, 3119]$ total counts (Turn $0$, raw counts $[1604, 3119]$, distance to 0 wrap $= 1604$ counts, distance to 4096 wrap $= 977$ counts).
  Neither axis crosses or approaches a wrap boundary during scanning or homing.
- **Permanent Open Directive**:
  This blind spot **must remain documented as a permanent open item**. If any future stage modification, slide holder redesign, or travel expansion requires an axis to straddle a 4096 boundary, the controller **must not rely on Mode 0 with raw direction matching**. Permanent remediation will require transitioning the actuators to continuous multi-turn mode (Mode 1 / Step Mode) or implementing an unwrapping-aware multi-point trajectory planner that subdivides boundary-crossing moves into micro-steps strictly $\le 1024$ counts with explicit turn tracking.

---

### 3. [RESOLVED] Root-Cause sys.path Import Shadowing from `combined_scan.py`
- **Issue**: Importing modules in `triple_scan_suite_runner.py` previously loaded a stale version of `autofocus.py` located at `D:\smart_scan\SmartCytoScan\autofocus.py`, which lacked recent fixes and parameter signatures.
- **Root Cause Identified**:
  In `combined_scan.py` (lines 46–54), a startup loop prepended `r"D:\smart_scan\SmartCytoScan"` directly to `sys.path[0]`:
  ```python
  # Legacy combined_scan.py
  for extra_path in [
      os.path.dirname(os.path.abspath(__file__)),
      r"D:\aaa_new_microscope",
      r"D:\smart_scan\SmartCytoScan",
  ]:
      if os.path.exists(extra_path) and extra_path not in sys.path:
          sys.path.insert(0, extra_path)
  ```
  When `from combined_scan import MicroscopeCamera` executed, it altered the global `sys.path` order, shadowing `D:\aaa_new_microscope\autofocus.py`.
- **Permanent Remediation**:
  1. Removed `r"D:\smart_scan\SmartCytoScan"` from `combined_scan.py`.
  2. Preserved the runner-level guard in `triple_scan_suite_runner.py` (`sys.path.remove(microscope_root); sys.path.insert(0, microscope_root)`) as defense-in-depth against any external imports.
- **Status**: **RESOLVED & CLEANED**.

---

### 4. [RESOLVED] Autofocus Call-Site Alignment & Production Verification
- **Previous Issue**: `triple_scan_suite_runner.py` called an unimported `sweep_optical_focus` with hardcoded `settle_sec=0.35`, `step=3`, `min_prominence=2.5`, and `resolution=(1920, 1080)`, while `autofocus.py` used `settle_sec=1.5`, `step=1`, `min_prominence=0.15`, and 4K `(3840, 2160)`.
- **Root Cause & Fix**:
  1. Replaced the disconnected call with direct delegation to canonical `run_autofocus_sweep()` from `autofocus.py`.
  2. Unified all operational parameters:
     - Dwell time: `settle_sec = 1.5s` (eliminating mechanical vibration blur).
     - Pitch: `step = 1 count` (high-precision top-down sweep).
     - Prominence: `min_prominence = 0.15`.
     - Resolution: native 4K UHD `(3840, 2160)`.
     - Backlash compensation: 25-count upward overshoot before settling downward into final lock.
  3. Restored default `--start-step` / `--af-start-step` to `1` across both files so unknown specimens receive a full corridor sweep by default, while preserving `--start-step 30` as an optional CLI flag for pre-calibrated slides.
- **Validation**: Full 308-tile scan completed across 14 rows $\times$ 22 columns with zero crashes, sharp focus across all tiles, and validated horizontal/vertical sharpness symmetry ($R_{\text{blur}} \approx 1.00$).
- **Status**: **RESOLVED & VERIFIED IN PRODUCTION**.

---

### 5. Unhardened Manual Tool Scripts (Silent `or 0` Fallback Debt)
- **Status**: The production path (`precision_tracker/servo_bus.py`) and primary CLI (`movements.py`) have been hardened with `_read_location_strict()`. However, four legacy diagnostic tools still contain vulnerable `or 0` fallbacks on register reads:
  1. `calibrate_endstops_step_by_step.py`
  2. `quick_test_min_dwell_max.py`
  3. `sweep_limits.py`
  4. `tools/return_stage_to_corridor_center.py`
- **Action Required**: Replace `or 0` on `read_current_location()` in these four tools with strict retry/raise helpers to eliminate silent failure masquerading as zero.

---

### 6. Non-Atomic Multi-File Rebaseline Tooling
- **Impact**: During Axis X rebaseline (Report 36), `rebaseline_x_axis.py` wrote files sequentially. A transient Windows file lock caused a `PermissionError` on the 4th file, leaving the system in a temporary split-brain state that required manual recovery.
- **Action Required**: Implement a true transactional two-phase commit utility for multi-file updates:
  - Write all targets to temporary files (`.tmp`).
  - Flush and verify all files on disk.
  - Perform atomic replace/rename operations across all targets in a single sequence.
  - Roll back from backups automatically if any file fails.

---

### 7. Misleading "Clean Exit Synchronization" in `movements.py`
- **Impact**: `movements.py` prints `Restoring startup motor position state... [PASS]` even if underlying register writes encounter communication retries or transient failures.
- **Action Required**: Validate the return value and readback confirmation of exit handlers before logging a successful synchronization message.

---

### 8. Systemic Architectural Technical Debt (from Assessment Report 37)
- **Version Control**: Initialized Git repository to track configuration, calibration, and codebase evolution across all investigations.
- **TOCTOU Configuration Risk**: 22 independent scripts parse `motor_limits.json` directly from disk instead of querying the central `AtomicCalibrationStore`. An edit to `motor_limits.json` during motion can cause Time-of-Check to Time-of-Use race conditions.
- **Hardcoded Connection Parameters**: Port `COM3`, baudrate `1000000`, and absolute paths `D:\aaa_new_microscope` are hardcoded across $>30$ individual scripts. These should be centralized in `config/system.json` or environment variables.
- **Dual Position Tracker Abstractions**: Both `MotorTracker` (in `motor_tracker.py`) and `PrecisionServoController` (in `precision_tracker/controller.py`) maintain multi-turn unwrapping logic. `MotorTracker` should be deprecated in favor of `PrecisionServoController`.

---

### 9. Additional Verification Tasks
- **Coordinated Multi-Axis Homing Test**: Verify simultaneous 3-axis homing (X, Y, Z) with active direction guards within current single-rotation bounds.
- **Pre-Scan Unified Health Check**: Create a standalone pre-flight script (`tools/preflight_check.py`) that queries bus voltage, servo temperatures, status error bits (`0x41`), holding torque states, and file consistency prior to scanning.

---

### 10. [OPEN GAP] Asynchronous Signal Abort (SIGINT / Ctrl+C) Race Condition Against os._exit(0)
- **Discovery Date**: September 30, 2026 (Scan suite abort forensics)
- **Root Cause & Mechanism**:
  When an operator issues Ctrl+C (SIGINT) during an active motion command in controller.move_to(), Python raises a KeyboardInterrupt which propagates up to the runner's global finally: block (in triple_scan_suite_runner.py). The finally: block executes controller.shutdown() and immediately terminates via os._exit(0).
  Because os._exit(0) terminates the process at the C-runtime level without waiting for ongoing serial bus I/O or ensuring actuator command completion:
  1. The servo may still hold an active goal position register write and continue traveling toward that waypoint until torque disable completes.
  2. If torque_disable() executes while the stage is coasting or under mechanical cable/spring tension, the axis can freewheel unbraked past safe limits.
- **Architectural Remediation Required**:
  Register an explicit OS signal handler for SIGINT (and SIGTERM) in PrecisionServoController:
  - Immediately read present location: c_raw = bus.read_present_position(sid).
  - Issue an instant goal-clamp write: bus.write_goal_position(sid, c_raw, speed=0) to freeze actuator motion with active holding torque before releasing bus control.
  - Synchronize and persist present positions to motor_state.json and config/state.json BEFORE the process is allowed to exit.
  - Avoid relying solely on a high-level script finally: block that a hard os._exit(0) can race past.

---

### 11. [OPEN GAP] Silent Exception Suppression via os._exit(0) in Runner Exit Handler
- **Discovery Date**: October 1, 2026 (Turn 2 homing abort investigation)
- **Root Cause & Mechanism**:
  In `triple_scan_suite_runner.py`, `safe_home_to_interior_start()` is called inside `main()`. If any unexpected hardware, communication, or motion fault occurs (e.g. `HardwareCommunicationError` from a dropped packet on the USB-serial bus, `GoalDirectionMismatchError`, `RuntimeError`, or a user interrupt), Python unwinds the stack straight into the global `finally:` block.
  The `finally:` block writes the manifest, closes the parallel movement logger, shuts down the controller, and unconditionally executes `os._exit(0)`.
  Because `os._exit(0)` immediately terminates the process at the C level, it bypasses Python's normal uncaught-exception handler. As a result, the traceback is never printed to `sys.stderr`, silently swallowing the real exception or interrupt that caused the abort and making post-mortem root-cause analysis unnecessarily difficult.
- **Architectural Remediation Required**:
  1. Capture the active exception context (`sys.exc_info()`) inside the `finally:` block (or wrap the main execution body in explicit `except Exception:` and `except KeyboardInterrupt:` blocks).
  2. Log the full exception type, message, and traceback directly to a persistent crash log (`scans/crash_report.log`) and print it cleanly to `sys.stderr`.
  3. Replace the hard `os._exit(0)` with a standard `sys.exit(exit_code)` once all hardware shutdown and I/O flushes are confirmed complete, preserving normal Python exit diagnostics.

---

### 12. [UNRESOLVED FINDING] Mystery Reset of Axis X EEPROM Offset Register 0x1F from 431 to 0
- **Discovery Date**: October 4, 2026 (Report 39 re-verification)
- **Status**: **UNRESOLVED / CAUSE UNKNOWN**
- **Symptom & Forensic Evidence**:
  During the comprehensive system state audit, live register interrogation of Axis X (Servo ID 5) revealed that EEPROM register `0x1F` (2-byte signed midpoint/zero position offset) returned `0` instead of the calibrated `431` established during earlier rebaseline investigations.
- **Forensic Codebase Audit**:
  Every script in the repository capable of issuing EEPROM write commands was audited line-by-line:
  1. `restore_factory_defaults.py`: Explicitly documented and verified via packet traces to exclude register `0x1F` from all write payloads.
  2. `calibrate_axis_midpoint.py`: Only executes against the targeted axis CLI argument; was never run against Axis X during this period.
  3. `calibrate_y.py`: Hardcoded strictly to Axis Y (Servo ID 3).
  4. `precision_tracker/servo_bus.py`: Contains low-level register write primitives, but no caller invokes an offset write to Servo ID 5.
  No script or automated workflow in the repository was found to have commanded an offset reset to 0.
- **Hypotheses & Next Steps**:
  Potential external triggers include:
  1. Power-cycle brownout or electrical transient on the serial bus causing an uncommitted or corrupted EEPROM page rewrite within the servo's internal microcontroller.
  2. Manual operator intervention via external Feetech software tools (e.g. FD / ST debug GUI) outside the repository's purview.
  3. Undocumented factory firmware behavior during certain stall/unlock sequences.
  This finding remains explicitly open and unresolved. Re-zeroing of Axis X's midpoint offset is deferred to future operator-supervised physical mechanical alignment.

---

### 13. [UNRESOLVED FINDING] Disappearance of `config/calibration.json` and `config/state.json` from Disk
- **Discovery Date**: October 4, 2026 (Report 39 re-verification)
- **Status**: **UNRESOLVED / CAUSE UNKNOWN** (Mitigation & Recovery Applied)
- **Symptom & Distinction from Write Errors**:
  During pre-flight verification, both `config/calibration.json` and `config/state.json` were found to be completely missing from disk.
  *Critical Clarification regarding Bug 8*: While Bug 8 remediated a Windows `PermissionError` when writing to a destination file marked `stat.S_IREAD` via `os.replace()`, **a failed `os.replace` call does NOT delete or unlink the destination file**. Under Win32 semantics, if `os.replace` fails with `Access is denied`, the destination file remains intact and unaltered. Therefore, the `os.chmod(S_IREAD)` write-failure mechanism does not and cannot account for the physical deletion of these files from disk.
- **Forensic Codebase Audit**:
  An exhaustive search across all repository scripts confirmed that no active code path invokes `os.remove()`, `os.unlink()`, `shutil.rmtree()`, or shell deletion commands on these configuration files.
- **Mitigation & Open Status**:
  1. `config/calibration.json` has been dynamically recompiled from `motor_limits.json` via `safe_stall_recovery.py`.
  2. `config/state.json` has been synthesized from live `motor_state.json`.
  3. `atomic_write_json()` in `precision_tracker/persistence.py` was enhanced to transparently handle read-only flags without throwing `PermissionError`.
  The original root cause for the unlinking event remains unsolved (hypothesized causes include manual filesystem operations, Git workspace operations such as branch switching or clean, or an unrecorded external script).

---

### 14. [AUDIT FINDING] Swapped Axis IDs in `update_verified_calibration.py` (Historical Impact Analysis)
- **Discovery Date**: October 5, 2026 (Code review audit)
- **Status**: **AUDITED / CONFIRMED BENIGN / FIXED**
- **Issue**:
  Line 58 of `update_verified_calibration.py` historically contained `axis_ids = {"X": 3, "Y": 5, "Z": 4}`, erroneously swapping the servo IDs for Axis X (canonical ID 5) and Axis Y (canonical ID 3).
- **Historical Impact Forensic Audit**:
  1. Git history reveals `update_verified_calibration.py` was committed during initial import (commit `67c94e36`, Sep 23, 2026) and was never modified until this audit.
  2. The script requires explicit console confirmation (`CONFIRM_RECALIBRATION` or `--auto-confirm`). No run logs, report artifacts, or shell histories document any execution of this script.
  3. Step 1 of `update_verified_calibration.py` copies `motor_limits.json` to `motor_limits.verified.json` using `shutil.copyfile()` bit-for-bit, which preserves the servo IDs already embedded inside the JSON structure and bypasses the faulty Python dictionary entirely.
  4. All historically committed versions of `config/calibration.json` (Sep 20 initial commit, Sep 28 commit `b3d4fa4e`) contain the correct mapping (`X: 5, Y: 3, Z: 4`). These were generated by `safe_stall_recovery.py`, which has always maintained the correct mapping.
- **Conclusion & Remediation**:
  No historical data in `motor_limits.verified.json` or `config/calibration.json` was corrupted. The mapping in `update_verified_calibration.py` has now been permanently corrected to `{"X": 5, "Y": 3, "Z": 4}`.
