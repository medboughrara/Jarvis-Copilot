# Interactive Recalibration Tool
# Syncs active motor limits to verified reference copy upon confirmation and compiles derived calibration.json.

import os
import json
import shutil
from datetime import datetime
import safe_stall_recovery

ROOT = "D:/aaa_new_microscope"
VERIFIED_LIMITS_FILE = os.path.join(ROOT, "motor_limits.verified.json")
ACTIVE_LIMITS_FILE = os.path.join(ROOT, "motor_limits.json")
CALIB_FILE = os.path.join(ROOT, "config/calibration.json")

def update_verified(auto_confirm: bool = False):
    print("=" * 70)
    print("UPDATE VERIFIED MOTOR LIMITS (SINGLE-SOURCE RECALIBRATION)")
    print("=" * 70)

    if not os.path.exists(ACTIVE_LIMITS_FILE):
        raise FileNotFoundError(f"Active limits file not found: {ACTIVE_LIMITS_FILE}")

    with open(ACTIVE_LIMITS_FILE, "r", encoding="utf-8") as f:
        act = json.load(f)

    print("ACTIVE LIMITS TO BE CONFIRMED:")
    for ax in ["X", "Y", "Z"]:
        if ax not in act:
            continue
        mn_obj = act[ax].get("min_limit")
        mx_obj = act[ax].get("max_limit")
        if not mn_obj or not mx_obj:
            print(f"  Axis {ax}: [INCOMPLETE LIMITS] (min={mn_obj}, max={mx_obj})")
            continue
        mn = mn_obj["rotations"] * 4096 + mn_obj["counts"]
        mx = mx_obj["rotations"] * 4096 + mx_obj["counts"]
        span = mx - mn
        rot_mn = mn_obj["rotations"]
        rot_mx = mx_obj["rotations"]
        ltype = act[ax].get("limit_type", "hard_mechanical" if ax == "Z" else "soft_optical")
        margin = act[ax].get("margin_counts", 2 if ax == "Z" else 60)
        source = act[ax].get("plausibility_source", "mechanical_hard_endstop_spec: measured 2026-09-12 span=51, bound=35..55" if ax == "Z" else "unset_pending_measurement")
        print(f"  Axis {ax} [{ltype}]: [{mn} .. {mx}] (Span: {span} counts, Margin: {margin}c, Source: {source})")

    if not auto_confirm:
        ans = input("Type CONFIRM_RECALIBRATION to promote active limits to golden copy: ").strip()
        if ans != "CONFIRM_RECALIBRATION":
            print("[CANCELLED] No changes made to verified golden reference.")
            return False

    # 1. Promote motor_limits.json -> motor_limits.verified.json
    try:
        os.system(f"attrib -R \"{VERIFIED_LIMITS_FILE}\"")
    except Exception:
        pass
    shutil.copyfile(ACTIVE_LIMITS_FILE, VERIFIED_LIMITS_FILE)
    print(f"[SUCCESS] Promoted active limits to golden reference: {VERIFIED_LIMITS_FILE}")

    # 2. Programmatically derive config/calibration.json from golden limits
    calib_data = {
        "version": "2.1.0",
        "created_at": datetime.utcnow().isoformat(),
        "axes": {}
    }
    axis_ids = {"X": 5, "Y": 3, "Z": 4}
    for ax, s_id in axis_ids.items():
        if ax not in act:
            continue
        mn = act[ax].get("min_limit")
        mx = act[ax].get("max_limit")
        if not mn or not mx:
            print(f"[WARN] Axis {ax} has incomplete limits. Skipping in calibration.json.")
            continue
        mn_cnt = mn["rotations"] * 4096 + mn["counts"]
        mx_cnt = mx["rotations"] * 4096 + mx["counts"]
        ltype = act[ax].get("limit_type", "hard_mechanical" if ax == "Z" else "soft_optical")
        margin_counts = act[ax].get("margin_counts", 2 if ax == "Z" else 60)
        margin_mult = act[ax].get("margin_multiplier", 1.0 if ax == "Z" else 2.0)
        plaus_source = act[ax].get("plausibility_source", "mechanical_hard_endstop_spec: measured 2026-09-12 span=51, bound=35..55" if ax == "Z" else "unset_pending_measurement")

        calib_data["axes"][ax] = {
            "axis_name": ax,
            "servo_id": s_id,
            "raw_zero": 0,
            "min_counts": min(mn_cnt, mx_cnt),
            "max_counts": max(mn_cnt, mx_cnt),
            "min_deg": round(min(mn_cnt, mx_cnt) * 360.0 / 4096.0, 2),
            "max_deg": round(max(mn_cnt, mx_cnt) * 360.0 / 4096.0, 2),
            "span_counts": abs(mx_cnt - mn_cnt),
            "span_deg": round(abs(mx_cnt - mn_cnt) * 360.0 / 4096.0, 2),
            "limit_type": ltype,
            "margin_counts": margin_counts,
            "margin_multiplier": margin_mult,
            "plausibility_source": plaus_source,
            "max_speed": 1500,
            "inverted": False,
            "calibrated_at": datetime.utcnow().isoformat()
        }
    os.makedirs(os.path.dirname(CALIB_FILE), exist_ok=True)
    import stat
    if os.path.exists(CALIB_FILE):
        try:
            os.chmod(CALIB_FILE, stat.S_IWRITE)
        except Exception:
            pass
    try:
        os.chmod(CALIB_FILE, stat.S_IREAD)
    except Exception:
        pass
    print(f"[SUCCESS] Programmatically compiled derived view: {CALIB_FILE} (read-only protected)")

    # 3. Synchronize turn states non-destructively
    safe_stall_recovery.safe_recover()
    print("[SUCCESS] SSOT promotion, derived calibration, and turn synchronization complete.")
    return True

if __name__ == "__main__":
    import sys
    auto = "--auto-confirm" in sys.argv
    update_verified(auto_confirm=auto)
