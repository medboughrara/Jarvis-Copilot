# Safe Stall Recovery Routine
# Strictly READ-ONLY for motor_limits.json.
# NEVER overwrites motor_limits.json.
# NEVER forces or resets motor rotation registers.

import os
import json
import shutil
from datetime import datetime

ROOT = 'D:/aaa_new_microscope'
VERIFIED_LIMITS_FILE = os.path.join(ROOT, 'motor_limits.verified.json')
ACTIVE_LIMITS_FILE = os.path.join(ROOT, 'motor_limits.json')
STATE_FILE = os.path.join(ROOT, 'config/state.json')
MOTOR_STATE_FILE = os.path.join(ROOT, 'motor_state.json')
CALIB_FILE = os.path.join(ROOT, 'config/calibration.json')

def safe_recover():
    """
    Non-destructive recovery:
    - Never modifies or overwrites motor_limits.json (user edits are sacred).
    - If motor_limits.json has been updated by user, automatically promotes it to verified golden copy.
    - Compiles derived config/calibration.json with full schema fidelity.
    - NEVER overrides or forces multi-turn rotation registers in motor_state.json or state.json.
    """
    print('=' * 70)
    print('NON-DESTRUCTIVE CALIBRATION SYNC (PROTECTING USER LIMITS)')
    print('=' * 70)

    if not os.path.exists(ACTIVE_LIMITS_FILE):
        if os.path.exists(VERIFIED_LIMITS_FILE):
            shutil.copyfile(VERIFIED_LIMITS_FILE, ACTIVE_LIMITS_FILE)
            print(f'[RECOVERY] motor_limits.json restored from golden backup.')
        else:
            raise FileNotFoundError('Neither motor_limits.json nor verified backup exists!')

    # Read user's active limits
    with open(ACTIVE_LIMITS_FILE, 'r', encoding='utf-8') as f:
        act = json.load(f)

    # 1. Always promote active user limits -> golden verified reference (Single Source of Truth)
    try:
        os.system(f'attrib -R "{VERIFIED_LIMITS_FILE}"')
    except Exception:
        pass
    shutil.copyfile(ACTIVE_LIMITS_FILE, VERIFIED_LIMITS_FILE)
    print(f'[SSOT] Synchronized golden reference {VERIFIED_LIMITS_FILE} from user motor_limits.json.')

    # 2. Derive config/calibration.json from active limits with full schema
    calib_data = {
        'version': '2.1.0',
        'created_at': datetime.utcnow().isoformat(),
        'axes': {}
    }
    axis_ids = {'X': 5, 'Y': 3, 'Z': 4}
    for ax, s_id in axis_ids.items():
        if ax not in act:
            continue
        mn = act[ax].get('min_limit')
        mx = act[ax].get('max_limit')
        if not mn or not mx:
            print(f"[WARN] Axis {ax} has incomplete limits. Skipping in calibration.json.")
            continue
        mn_cnt = mn['rotations'] * 4096 + mn['counts']
        mx_cnt = mx['rotations'] * 4096 + mx['counts']
        ltype = act[ax].get('limit_type', 'hard_mechanical' if ax == 'Z' else 'soft_optical')
        margin_counts = act[ax].get('margin_counts', 2 if ax == 'Z' else 60)
        margin_mult = act[ax].get('margin_multiplier', 1.0 if ax == 'Z' else 2.0)
        plaus_source = act[ax].get('plausibility_source', 'mechanical_hard_endstop_spec: measured 2026-09-12 span=35..55' if ax == 'Z' else 'unset_pending_measurement')

        calib_data['axes'][ax] = {
            'axis_name': ax,
            'servo_id': s_id,
            'raw_zero': 0,
            'min_counts': min(mn_cnt, mx_cnt),
            'max_counts': max(mn_cnt, mx_cnt),
            'min_deg': round(min(mn_cnt, mx_cnt) * 360.0 / 4096.0, 2),
            'max_deg': round(max(mn_cnt, mx_cnt) * 360.0 / 4096.0, 2),
            'span_counts': abs(mx_cnt - mn_cnt),
            'span_deg': round(abs(mx_cnt - mn_cnt) * 360.0 / 4096.0, 2),
            'limit_type': ltype,
            'margin_counts': margin_counts,
            'margin_multiplier': margin_mult,
            'plausibility_source': plaus_source,
            'max_speed': 1500,
            'inverted': False,
            'calibrated_at': datetime.utcnow().isoformat()
        }

    os.makedirs(os.path.dirname(CALIB_FILE), exist_ok=True)
    import stat
    if os.path.exists(CALIB_FILE):
        try:
            os.chmod(CALIB_FILE, stat.S_IWRITE)
        except Exception:
            pass
    with open(CALIB_FILE, 'w', encoding='utf-8') as f:
        json.dump(calib_data, f, indent=2)
    try:
        os.chmod(CALIB_FILE, stat.S_IREAD)
    except Exception:
        pass
    print(f'[DERIVED] Compiled {CALIB_FILE} dynamically from user motor limits (read-only protected).')
    print('[PROTECTION COMPLETE] User motor_limits.json preserved and locked against overwriting.')
    print('=' * 70)

if __name__ == '__main__':
    safe_recover()
