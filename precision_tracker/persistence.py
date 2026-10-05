"""
Phase 4: Atomic Persistence Layer.
Implements crash-resilient write-to-temp-then-atomic-rename (os.replace) for state and calibration files.
"""
import os
import json
import tempfile
import logging
from typing import Optional
from .schemas import SystemState, SystemCalibration

logger = logging.getLogger("precision_tracker.persistence")

DEFAULT_STATE_FILE = "D:/aaa_new_microscope/config/state.json"
DEFAULT_CALIBRATION_FILE = "D:/aaa_new_microscope/config/calibration.json"


def atomic_write_json(file_path: str, data_dict: dict, make_readonly: bool = False):
    """
    Atomically writes JSON data to file_path.
    1. Writes to a temporary file in the same directory.
    2. Flushes and syncs to disk (os.fsync).
    3. Handles Windows read-only destination attributes seamlessly.
    4. Atomically replaces target file using os.replace.
    5. Restores read-only protection if destination was originally read-only or requested.
    6. Cleans up temp file on failure.
    """
    directory = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(directory, exist_ok=True)

    temp_fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".tmp_state_", suffix=".json")
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        import stat
        was_readonly = make_readonly
        if os.path.exists(file_path):
            try:
                mode = os.stat(file_path).st_mode
                if not (mode & stat.S_IWRITE):
                    was_readonly = True
                    os.chmod(file_path, stat.S_IWRITE)
            except Exception:
                pass

        # Atomic rename with retry loop for Windows file locking
        import time as _time
        for attempt in range(4):
            try:
                os.replace(temp_path, file_path)
                break
            except PermissionError:
                if attempt < 3:
                    if os.path.exists(file_path):
                        try:
                            os.chmod(file_path, stat.S_IWRITE)
                        except Exception:
                            pass
                    _time.sleep(0.02)
                else:
                    raise

        if was_readonly and os.path.exists(file_path):
            try:
                os.chmod(file_path, stat.S_IREAD)
            except Exception:
                pass
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        logger.error(f"[PERSISTENCE] Atomic write failed for {file_path}: {e}")
        raise e


class AtomicStateStore:
    """Manages atomic loading and saving of runtime SystemState."""

    def __init__(self, file_path: str = DEFAULT_STATE_FILE):
        self.file_path = file_path

    def load(self) -> Optional[SystemState]:
        """Loads state from disk. Returns None if file does not exist or is corrupted."""
        if not os.path.exists(self.file_path):
            logger.info(f"[STATE] No existing state file at {self.file_path}.")
            return None
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SystemState.from_dict(data)
        except Exception as e:
            logger.error(f"[STATE] Error reading state file {self.file_path}: {e}")
            return None

    def save(self, state: SystemState):
        """Atomically saves SystemState to disk."""
        atomic_write_json(self.file_path, state.to_dict())


class AtomicCalibrationStore:
    """Manages atomic loading and saving of SystemCalibration."""

    def __init__(self, file_path: str = DEFAULT_CALIBRATION_FILE):
        self.file_path = file_path

    def load(self) -> Optional[SystemCalibration]:
        """Loads calibration from disk."""
        if not os.path.exists(self.file_path):
            logger.info(f"[CALIB] No existing calibration file at {self.file_path}.")
            return None
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SystemCalibration.from_dict(data)
        except Exception as e:
            logger.error(f"[CALIB] Error reading calibration file {self.file_path}: {e}")
            return None

    def save(self, calibration: SystemCalibration):
        """Atomically saves SystemCalibration to disk."""
        atomic_write_json(self.file_path, calibration.to_dict())
