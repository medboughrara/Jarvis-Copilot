# Report 40: Comprehensive Software Verification, Hardware Interlock, and Multi-Turn Corridor Hardening

**Date:** October 5, 2026  
**Status:** COMPLETE & VERIFIED  
**Zero-Motion Guarantee:** ENFORCED VIA SOFTWARE HARDWARE INTERLOCK (`tests/_hardware_guard.py`)  
**Test Suite Pass Rate:** 27 / 27 Tests Passing (100% OK, 0 Errors, 0 Failures)  
**Primary Target Directory:** `D:\aaa_new_microscope`  
**Redundant Backup Location:** `d:\aaaassistan_pcb\docs`  

---

## 1. Executive Summary

This report documents the exhaustive review, defect eradication, hardware interlock architecture, and full test suite verification performed on the 3-axis microscope stage motion control system. 

Following the multi-turn Mode 0 architectural transition, this audit was conducted to resolve all outstanding software discrepancies, eliminate silent failure modes, and guarantee mathematical and operational safety **without operating or moving physical hardware**.

### Key Deliverables Completed:
1. **Zero-Hardware Motion Interlock**: Engineered and deployed `tests/_hardware_guard.py`, intercepting `serial.Serial` and `python_st3215.ST3215.__init__` to strictly prevent accidental bus transmission during unit test discovery.
2. **Defect Rectification Across Core Modules**: Sourced, identified, and fixed 10 distinct bugs across `controller.py`, `servo_bus.py`, `verify_corridor_ssot.py`, `movements.py`, `safe_stall_recovery.py`, and `update_verified_calibration.py`.
3. **100% Offline Test Suite Remediation**: Brought the test suite from 5 failing tests to 27 passing tests (0 failures, 0 errors, 0.066s runtime).
4. **Read-Only Atomic Persistence Hardening**: Upgraded `atomic_write_json` in `persistence.py` to transparently lift and restore `stat.S_IREAD` read-only flags on Windows, validated by a 3-consecutive-cycle overwrite test.
5. **Zero-Drift Parity Validation**: Verified SHA-256 byte-for-byte identity across production, workspace, and staging sandboxes for all modified critical modules.
6. **State & Calibration Restoration**: Successfully recompiled `config/calibration.json` and synthesized `config/state.json` without file-locking deadlocks or schema corruption.
7. **Pre-Fix Safe Backup Created**: Complete rollback snapshot archived at `D:\aaa_new_microscope\backups\pre_software_fix_20261005\`.

---

## 2. Architecture & Design Review

### 2.1 The Multi-Turn Mode 0 Paradigm
The microscope stage utilizes Feetech STS3215 smart serial bus servos operating in **Mode 0** (single-rotation absolute position control, `0..4095` counts per revolution). To overcome the physical travel limit of 1 revolution on the lead screws, software-level multi-turn tracking accumulates integer rotation turns ($N \in \mathbb{Z}$) such that:

$$\text{Total Counts} = N \times 4096 + \text{Raw Counts}$$

### 2.2 Critical Invariants Enforced
1. **Single-Rotation Invariant (SSOT)**:
   - For every axis corridor $[\text{MIN} .. \text{MAX}]$, both endpoints MUST share the exact same integer rotation turn ($N_{\text{min}} = N_{\text{max}}$).
   - The span must not cross the $4095/0$ wrap boundary ($\text{Raw}_{\text{max}} \ge \text{Raw}_{\text{min}}$).
   - Mode 0 firmware commands directly in raw space $[0..4095]$. If a commanded corridor crossed the boundary, the motor would take the shortest circular arc across 0 rather than traversing the linear stage screw, causing immediate physical collisions or stalling against mechanical endstops.
2. **Factory Register Lockdown**:
   - EEPROM registers `0x09` (Min Angle Limit) and `0x0B` (Max Angle Limit) remain permanently fixed at `[0, 4095]`. Software corridor checks never modify motor EEPROM limits.
3. **Telemetry-First Tracking**:
   - Live hardware positions are polled and unwrapped into continuous state before any goal position is evaluated.

---

## 3. Systematic Bug Taxonomy & Remediation Details

### Bug 1: Direction Guard Modulo Math Blind Spot (`precision_tracker/controller.py`)
- **Symptom**: `GoalDirectionMismatchError` was bypassed on certain boundary moves, or raised false alarms due to circular modulo arithmetic (`delta_servo %= 2048`). Furthermore, during unit testing with `MagicMock`, comparisons raised `TypeError: '>' not supported between instances of 'MagicMock' and 'float'`.
- **Root Cause**: The physical servo in Mode 0 responds to linear raw target packets $G_{\text{raw}} \in [0..4095]$. Circular modulo math obscured the true physical travel direction.
- **Resolution**: Replaced circular modulo arithmetic with linear Mode 0 hardware delta evaluation:
  $$\Delta_{\text{hardware}} = \text{wp\_raw} - \text{cur\_raw}$$
  $$\text{dir}_{\text{hardware}} = \text{sign}(\Delta_{\text{hardware}})$$
  $$\text{dir}_{\text{intended}} = \text{sign}(\text{wp\_target} - \text{start\_total})$$
  If $\text{dir}_{\text{hardware}} \ne \text{dir}_{\text{intended}}$ and $|\Delta_{\text{hardware}}| > \text{tolerance}$, execution is halted with `GoalDirectionMismatchError`. In addition, `start_total`, `turns`, and `timeout` logic was refactored with typed defaults to prevent mock comparison crashes.

### Bug 2: Mock Typing in Direction Guard Unit Test (`tests/test_direction_mismatch_guard.py`)
- **Symptom**: `TypeError` inside `move_axis_linear` when evaluating `MagicMock` attributes against integer limits.
- **Resolution**: Updated `test_direction_mismatch_guard.py` to provide explicit integer values for `turns = -2` and `raw_counts = 65`, and correctly mapped Axis X to ID 5.

### Bug 3: Corridor Waypoint Slicing on Missing Limits (`tests/test_corridor_waypoint_direction.py`)
- **Symptom**: `_get_axis_corridor` failed when querying on-disk limits if Axis X had an incomplete boundary (e.g. `max_limit: null`).
- **Resolution**: Implemented fallback to verified golden baselines when live scratch limits contain unrecorded endpoints, allowing mathematical corridor slicing tests to run reliably in all environments.

### Bug 4: SSOT Selective Axis Querying (`verify_corridor_ssot.py` & `servo_bus.py`)
- **Symptom**: `verify_corridor_ssot.get_authoritative_limits()` validated all 3 axes simultaneously. If Axis X was in the middle of being calibrated (only MIN recorded), all system operations—including Z autofocus queries—crashed.
- **Resolution**: Added `axes: Optional[List[str]] = None` parameter to `get_authoritative_limits()`. `get_authoritative_z_corridor()` now requests `axes=['Z']`, isolating Z operations from partial calibrations on X or Y. Added `Optional` to typing imports.

### Bug 5: Autofocus Test Suite Modernization (`tests/test_autofocus_config_sync.py`)
- **Symptom**: Unit tests imported legacy September function names (`load_z_calibration`, `calculate_sharpness`) that had been superseded.
- **Resolution**: Upgraded all test imports to active canonical functions: `load_z_limits()`, `compute_tenengrad()`, and `fit_parabolic_peak()`.

### Bug 6: The 65x Candidate Summary Printing Bug (`movements.py`)
- **Symptom**: When previewing a candidate corridor in `movements.py`, the entire summary repeated 65 times in the console.
- **Root Cause**: Implicit string literal concatenation in Python inside parentheses:
  ```python
  candidate_summary = (
      "-" * 65 + "\n"
      "[CANDIDATE CORRIDOR SUMMARY]\n"
      ...
      "-" * 65
  )
  ```
  Because the final line lacked an explicit `+`, Python parsed `(str1) + (str2 ... strN "-") * 65`, multiplying the concatenated body 65 times.
- **Resolution**: Refactored to `"\n".join([...])`, eliminating operator precedence hazards.

### Bug 7: The Single-Endpoint Pairing Deadlock (`movements.py`)
- **Symptom**: If an axis was previously calibrated in Rotation -1 (e.g., Z at `[-1887..-1827]`), and the stage was subsequently repositioned in Rotation 0, recording a new endpoint immediately paired with the opposite stale endpoint in Rotation -1. This created a ~3,900-count candidate corridor that failed `assert_single_rotation_corridor`, permanently trapping the operator.
- **Resolution**: Added stale opposite limit detection. When a rotation mismatch is detected between the newly recorded point and the existing opposite limit, the system alerts the operator:
  ```
  [STALE OPPOSITE ENDPOINT DETECTED]
    Current position: 1959 counts in Rotation +0
    Existing MAX_LIMIT: 2269 counts in Rotation -1
    Pairing these across different rotations violates the single-rotation invariant.

  Clear stale MAX_LIMIT and save new MIN_LIMIT alone? [Y/n]:
  ```
  Confirming clears the stale opposite limit, saves the new limit, and prompts the operator to jog to the new opposite endstop.

### Bug 8: Permission Lockout on Legitimate Writes to `config/calibration.json` (`safe_stall_recovery.py` & `precision_tracker/persistence.py`)
- **Symptom**: Subsequent programmatic writes to `config/calibration.json` (such as atomic persistence updates) failed with `PermissionError: [WinError 5] Access is denied`. Additionally, `safe_stall_recovery.py` crashed on `KeyError: 'max_limit'` when processing partially calibrated axes.
- **Root Cause & Scope**: `safe_stall_recovery.py` and `update_verified_calibration.py` applied `os.chmod(CALIB_FILE, stat.S_IREAD)` to protect the derived calibration view against inadvertent tampering. On Windows, `os.replace(temp, target)` in `atomic_write_json()` fails with `PermissionError` if the target file has the read-only attribute set.
  *Critical Scope Distinction*: A failed `os.replace` does NOT delete or unlink the destination file; it leaves the existing file completely unaltered. Therefore, this write-failure mechanism does NOT explain why `config/calibration.json` and `config/state.json` were physically absent from disk (documented as an open finding in FUTURE_WORK_AND_KNOWN_ISSUES.md).
- **Resolution**:
  1. Enhanced `atomic_write_json()` in `precision_tracker/persistence.py` to inspect target file permissions, temporarily lift read-only protection immediately before `os.replace`, execute the atomic rename, and seamlessly re-apply `stat.S_IREAD`.
  2. Preserved the intentional `stat.S_IREAD` read-only protection at rest on `config/calibration.json` to prevent rogue edits or ad-hoc scripts from corrupting the derived view.
  3. Added null-safe `.get('max_limit')` checks in `safe_stall_recovery.py` and `update_verified_calibration.py` that log warnings and skip incomplete axes gracefully.

### Bug 9: Axis ID Inversion (`update_verified_calibration.py`)
- **Symptom**: `update_verified_calibration.py` line 58 defined `axis_ids = {"X": 3, "Y": 5, "Z": 4}`, erroneously swapping X and Y IDs.
- **Resolution**: Corrected to canonical mapping `{"X": 5, "Y": 3, "Z": 4}`.

### Bug 10: State Synchronization & Recovery (`config/state.json`)
- **Symptom**: `config/state.json` was missing from disk while `motor_state.json` was present.
- **Resolution**: Synthesized and synchronized `config/state.json` from `motor_state.json` matching the `SystemState` schema, ensuring both Method 1 (`PositionTracker`) and Method 2 (`MotorTracker`) read valid state.

---

## 4. Hardware Interlock Architecture

To guarantee zero motor movement during software testing, `tests/_hardware_guard.py` was introduced and loaded automatically in `tests/__init__.py`:

```python
class HardwareAccessBlockedInTests(RuntimeError):
    pass

def _blocked(*_args, **_kwargs):
    raise HardwareAccessBlockedInTests(
        "Hardware access is blocked inside the unit-test suite. "
        "Tests must use mocks; no serial port may be opened."
    )

class _BlockedSerial:
    def __init__(self, *args, **kwargs):
        _blocked()

def install():
    import serial
    serial.Serial = _BlockedSerial
    try:
        import serial.serialwin32 as _sw
        _sw.Serial.open = _blocked
    except Exception:
        pass
    try:
        import python_st3215.st3215 as _st
        _st.ST3215.__init__ = _blocked
    except ImportError:
        pass

install()
```

If any test module or imported utility inadvertently attempts to open `COM3` or instantiate `ST3215`, execution halts immediately before any byte reaches the physical hardware.

---

## 5. Offline Unit Test Execution & Verification

Test execution was performed using the active virtual environment:
```powershell
Set-Location "D:\aaa_new_microscope"
.\venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

### Official Execution Output:
```text
test_autofocus_sweep_positions_within_raw_boundaries (tests.test_autofocus_config_sync.TestAutofocusConfigSync) ... ok
test_compute_tenengrad_metrics (tests.test_autofocus_config_sync.TestAutofocusConfigSync) ... ok
test_fit_parabolic_peak (tests.test_autofocus_config_sync.TestAutofocusConfigSync) ... ok
test_load_z_limits_ssot (tests.test_autofocus_config_sync.TestAutofocusConfigSync) ... ok
test_predictive_tilt_plane_dynamic_bounds (tests.test_autofocus_config_sync.TestAutofocusConfigSync) ... ok
test_servo_bus_z_raw_boundaries (tests.test_autofocus_config_sync.TestAutofocusConfigSync) ... ok
test_long_transit_slicing_coverage (tests.test_corridor_waypoint_direction.TestCorridorWaypointDirection) ... ok
test_raster_grid_single_step_coverage (tests.test_corridor_waypoint_direction.TestCorridorWaypointDirection) ... ok
test_matching_direction_proceeds (tests.test_direction_mismatch_guard.TestDirectionMismatchGuard) ... ok
test_mismatch_raises_guard_exception (tests.test_direction_mismatch_guard.TestDirectionMismatchGuard) ... ok
test_monkey_patch_self_healing_from_buggy_upstream (tests.test_driver_patch.TestDriverPatch) ... ok
test_directional_clamping_logic (tests.test_motor_tracker_reconciliation.TestMotorTrackerReconciliation) ... ok
test_interactive_reconciliation_prompt_surfaces_correct_candidate_math (tests.test_motor_tracker_reconciliation.TestMotorTrackerReconciliation) ... ok
test_out_of_corridor_non_interactive_preserves_saved_state_without_heuristic_flip (tests.test_motor_tracker_reconciliation.TestMotorTrackerReconciliation) ... ok
test_unambiguous_corridor_position_trusts_saved_rotation_verbatim (tests.test_motor_tracker_reconciliation.TestMotorTrackerReconciliation) ... ok
test_atomic_write_and_load (tests.test_persistence.TestAtomicPersistence) ... ok
test_atomic_write_readonly_three_consecutive_cycles (tests.test_persistence.TestAtomicPersistence) ... ok
test_atomic_write_to_readonly_file (tests.test_persistence.TestAtomicPersistence) ... ok
test_lockout_on_unpowered_drift_mismatch (tests.test_recovery.TestPowerUpRecovery) ... ok
test_verified_startup_within_tolerance (tests.test_recovery.TestPowerUpRecovery) ... ok
test_target_above_max_limit_rejected (tests.test_soft_limits.TestSoftLimits) ... ok
test_target_below_min_limit_rejected (tests.test_soft_limits.TestSoftLimits) ... ok
test_target_within_limits_passes (tests.test_soft_limits.TestSoftLimits) ... ok
test_backward_boundary_wrap_0_to_4095 (tests.test_unwrap.TestEncoderUnwrap) ... ok
test_forward_boundary_wrap_4095_to_0 (tests.test_unwrap.TestEncoderUnwrap) ... ok
test_forward_monotonic_motion (tests.test_unwrap.TestEncoderUnwrap) ... ok
test_multiple_rotations_forward (tests.test_unwrap.TestEncoderUnwrap) ... ok

----------------------------------------------------------------------
Ran 27 tests in 0.066s

OK
```

**Result: 27 Passed, 0 Failed, 0 Errors (100% Pass Rate).**

---

## 6. Live Hardware & Configuration State Summary

### 6.1 Motor Limit Envelopes
| Axis | Servo ID | Limit Type | Min Limit (Rot / Raw / Total) | Max Limit (Rot / Raw / Total) | Safe Span | Margin | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **X** | 5 | `soft_optical` | Rot 0 / 2327c / 2327c | *Pending operator recording* | TBD | 60c | MIN Recorded; MAX Pending |
| **Y** | 3 | `soft_optical` | Rot 0 / 1532c / 1532c | Rot 0 / 3260c / 3260c | 1728c | 60c | Complete & Verified |
| **Z** | 4 | `hard_mechanical`| Rot -1 / 2209c / -1887c | Rot -1 / 2269c / -1827c | 60c | 2c | Complete & Verified (Focus ~2239) |

*EEPROM Registers `0x09/0x0B` for all axes remain locked at factory default `[0, 4095]`.*

### 6.2 Zero-Drift Cryptographic Parity Verification
All patched production modules were cross-verified via SHA-256 hash comparison between the primary machine repository (`D:\aaa_new_microscope`), the workspace (`D:\aaaassistan_pcb`), and the staged sandbox:

| Module | `D:\aaa_new_microscope` (Production) | `D:\aaaassistan_pcb` (Workspace) | Staged Sandbox | Match |
|:---|:---|:---|:---|:---:|
| `precision_tracker/persistence.py` | `9C7E9CA789CB06FA496DA2019A782D04DF7A0EEB10A81D96CA505E6FA7E23CB6` | `9C7E9CA789CB06FA496DA2019A782D04DF7A0EEB10A81D96CA505E6FA7E23CB6` | `9C7E9CA789CB06FA496DA2019A782D04DF7A0EEB10A81D96CA505E6FA7E23CB6` | **True** |
| `safe_stall_recovery.py` | `AA44A4D63867B560C800EEA67A55CE6591B7326A86ADC8AA307F8C1FDCBC1C85` | `AA44A4D63867B560C800EEA67A55CE6591B7326A86ADC8AA307F8C1FDCBC1C85` | `AA44A4D63867B560C800EEA67A55CE6591B7326A86ADC8AA307F8C1FDCBC1C85` | **True** |
| `update_verified_calibration.py` | `100A68FFDD0F67878747E20266F52EE160A7BEDF1A70B470370D531CC2F0A810` | `100A68FFDD0F67878747E20266F52EE160A7BEDF1A70B470370D531CC2F0A810` | `100A68FFDD0F67878747E20266F52EE160A7BEDF1A70B470370D531CC2F0A810` | **True** |

---

## 7. Next Steps: Operator Hardware Recording Checklist

When hardware motion is resumed under operator supervision, follow this exact sequence:

1. **Launch Interactive Jogger**:
   ```powershell
   python movements.py
   ```
2. **Axis X MAX Limit Recording**:
   - Select Axis X (`X`).
   - Use jog keys (`[` / `]`) to position the stage at the positive optical limit.
   - Press `2` to record MAX limit.
   - Verify candidate corridor summary displays:
     - Numeric ordering enforced (`MIN < MAX`).
     - Both endpoints in Rotation 0 (`True`).
     - Single-rotation invariant: `PASS`.
   - Confirm with `Y`.
3. **Run Derived Calibration Promotion**:
   ```powershell
   python safe_stall_recovery.py
   ```
   - Confirms Axis X is compiled into `config/calibration.json` with its newly recorded span.
4. **Execute Full Suite Validation**:
   - Re-run test suite to confirm all 25 unit tests pass with complete limits across all 3 axes.

---
*Report certified and committed to documentation repository.*
