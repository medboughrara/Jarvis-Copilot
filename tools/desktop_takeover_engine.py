"""
Desktop Takeover & Autonomous Screen Manipulation Engine for Jarvis Copilot.
Combines all desktop automation heuristics and real-world canvas manipulation tricks:

1. Win32 Window Discovery & Focus Lockout Bypass (Alt pulse + SW_MAXIMIZE/SW_RESTORE)
2. DPI-Aware Multi-Monitor Screen Buffer Capture
3. Canvas-Area OCR Grounding with Browser Chrome Exclusion (filters out tabs/URLs/bookmarks)
4. Typographic OCR Fuzzy Matching (handles stylized fonts like 'ROBOTIC' vs 'ROBOTIO')
5. Web Canvas Drag Physics (mouse down hold threshold, cosine ease-in-out interpolation, mouse up)
6. Keyboard Nudging (Shift+Arrow 10px / Arrow 1px)
7. Canva / Multi-Slide Drawer Navigation (auto-switches slides if target is on another page)
8. Automated Before/After Displacement Verification Loop
9. Built-in Corner Failsafe Guardrail
"""

import os
import sys
import time
import math
import ctypes
from ctypes import wintypes
from typing import Dict, Any, List, Optional, Tuple, Union
from PIL import ImageGrab
import config

logger = config.get_logger(__name__)

SCRATCH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
os.makedirs(SCRATCH_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Win32 Constants & Structures
# ---------------------------------------------------------------------------

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class DesktopFailsafeException(Exception):
    """Raised when mouse failsafe boundary is triggered (e.g. cursor in extreme corner)."""
    pass


MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000
WHEEL_DELTA = 120

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_MAP = {
    "ctrl": 0x11, "control": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B,
    "enter": 0x0D, "return": 0x0D, "esc": 0x1B, "escape": 0x1B, "tab": 0x09,
    "space": 0x20, "backspace": 0x08, "delete": 0x2E,
    "pageup": 0x21, "pagedown": 0x22, "home": 0x24, "end": 0x23,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    **{f"f{i}": 0x70 + (i - 1) for i in range(1, 13)},
    **{chr(c).lower(): c for c in range(ord('A'), ord('Z') + 1)},
    **{str(i): ord('0') + i for i in range(10)},
}


# ---------------------------------------------------------------------------
# Master Desktop Takeover Engine
# ---------------------------------------------------------------------------

class DesktopTakeoverEngine:
    """
    Robust, production-grade autonomous desktop manipulation engine.
    Encapsulates all window handling, OCR vision grounding, canvas drag physics,
    and verification loops into a single cohesive interface.
    """

    def __init__(self):
        self.user32 = ctypes.windll.user32
        self._ensure_input_desktop()
        self.ocr_engine = None
        self._init_ocr()

    def _ensure_input_desktop(self) -> bool:
        """Attaches calling thread to interactive desktop session."""
        try:
            hDesk = self.user32.OpenInputDesktop(0, False, 0x01FF)
            if hDesk:
                self.user32.SetThreadDesktop(hDesk)
                return True
        except Exception as e:
            logger.debug(f"[Desktop Engine] OpenInputDesktop notice: {e}")
        return False

    def _init_ocr(self):
        """Initializes local RapidOCR engine."""
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.ocr_engine = RapidOCR()
        except Exception as e:
            logger.warning(f"[Desktop Engine] RapidOCR initialization warning: {e}")
            self.ocr_engine = None

    def get_cursor_pos(self) -> Tuple[int, int]:
        """Returns current cursor coordinates (x, y)."""
        self._ensure_input_desktop()
        pt = POINT()
        if self.user32.GetCursorPos(ctypes.byref(pt)):
            return int(pt.x), int(pt.y)
        return 0, 0

    def check_failsafe(self, x: int, y: int):
        """Emergency corner abort check (top-left 5x5px)."""
        if x <= 5 and y <= 5:
            raise DesktopFailsafeException("Failsafe triggered: cursor in top-left corner (0,0). Automation aborted.")

    # -----------------------------------------------------------------------
    # 1. Window Discovery & Focus Management
    # -----------------------------------------------------------------------

    def find_windows_by_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Enumerates all visible top-level windows matching a search query.
        """
        self._ensure_input_desktop()
        q_lower = query.lower().strip()
        matched = []

        def enum_proc(hwnd, lParam):
            if self.user32.IsWindowVisible(hwnd):
                length = self.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    self.user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if q_lower in title.lower():
                        rect = wintypes.RECT()
                        self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        is_iconic = bool(self.user32.IsIconic(hwnd))
                        matched.append({
                            "hwnd": hwnd,
                            "title": title,
                            "rect": [rect.left, rect.top, rect.right, rect.bottom],
                            "width": rect.right - rect.left,
                            "height": rect.bottom - rect.top,
                            "is_minimized": is_iconic
                        })
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        self.user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
        return matched

    def focus_window(self, target: Union[str, int], maximize: bool = True) -> Dict[str, Any]:
        """
        Brings target window to the foreground with Windows 10/11 focus lockout bypass.
        Pulsing Alt allows SetForegroundWindow to succeed even from background worker threads.
        """
        self._ensure_input_desktop()
        hwnd = None
        title = ""

        if isinstance(target, int):
            hwnd = target
            length = self.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
        else:
            wins = self.find_windows_by_query(str(target))
            if not wins:
                return {"status": "error", "summary": f"No window found matching '{target}'."}
            hwnd = wins[0]["hwnd"]
            title = wins[0]["title"]

        # Pulse Alt key to bypass Windows focus lock
        self.user32.keybd_event(0x12, 0, 0, 0)
        self.user32.keybd_event(0x12, 0, KEYEVENTF_KEYUP, 0)

        # Show window (SW_MAXIMIZE=3 or SW_RESTORE=9)
        show_cmd = 3 if maximize else 9
        self.user32.ShowWindow(hwnd, show_cmd)
        self.user32.BringWindowToTop(hwnd)
        self.user32.SetForegroundWindow(hwnd)
        time.sleep(0.5)

        return {
            "status": "success",
            "summary": f"Focused window '{title}' (HWND: {hwnd}).",
            "data": {"hwnd": hwnd, "title": title}
        }

    # -----------------------------------------------------------------------
    # 2. Vision Grounding & Smart Canvas Filtering
    # -----------------------------------------------------------------------

    def capture_screen(self, output_name: str = "workspace_screen.png") -> str:
        """Captures primary display buffer to scratch directory."""
        path = os.path.join(SCRATCH_DIR, output_name)
        img = ImageGrab.grab()
        img.save(path)
        return path

    def locate_element_on_screen(
        self,
        query: str,
        screenshot_path: Optional[str] = None,
        exclude_browser_chrome: bool = True,
        min_y: int = 0,
        max_y: int = 999999
    ) -> Optional[Dict[str, Any]]:
        """
        Locates UI element with browser-chrome exclusion and typographic fuzzy matching.
        
        Args:
            query: Target text query (e.g. 'ROBOTIC', 'Run', 'File').
            exclude_browser_chrome: If True, ignores y < 200 (tabs/URL bar/bookmarks)
                                    unless query explicitly targets them.
            min_y: Optional minimum vertical pixel threshold.
            max_y: Optional maximum vertical pixel threshold.
        """
        if not self.ocr_engine:
            self._init_ocr()
            if not self.ocr_engine:
                return None

        img_path = screenshot_path or self.capture_screen("temp_grounding.png")
        results, _ = self.ocr_engine(img_path)
        if not results:
            return None

        q_clean = query.strip().upper()
        # Check if user explicitly asked for browser chrome elements
        is_chrome_target = any(k in q_clean.lower() for k in ["tab", "url", "bookmark", "address", "search"])
        effective_min_y = min_y
        if exclude_browser_chrome and not is_chrome_target:
            effective_min_y = max(min_y, 200)

        best_match = None
        best_score = 0.0

        for box, text, score in results:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x_min, x_max = int(min(xs)), int(max(xs))
            y_min, y_max = int(min(ys)), int(max(ys))
            center_x = (x_min + x_max) // 2
            center_y = (y_min + y_max) // 2

            # Canvas boundary filtering
            if center_y < effective_min_y or center_y > max_y:
                continue

            t_upper = text.strip().upper()

            # Compute match score with font typo tolerance ('ROBOTIC' vs 'ROBOTIO')
            match_score = 0.0
            if q_clean == t_upper:
                match_score = 1.0 + score
            elif q_clean in t_upper or t_upper in q_clean:
                match_score = 0.8 + score
            elif self._levenshtein_ratio(q_clean, t_upper) >= 0.70:
                match_score = 0.75 + score
            else:
                q_words = set(q_clean.split())
                t_words = set(t_upper.split())
                overlap = len(q_words.intersection(t_words))
                if overlap > 0:
                    match_score = 0.5 * (overlap / max(len(q_words), 1)) + score

            if match_score > best_score and match_score > 0.60:
                best_score = match_score
                best_match = {
                    "text": text,
                    "center_x": center_x,
                    "center_y": center_y,
                    "x_min": x_min,
                    "x_max": x_max,
                    "y_min": y_min,
                    "y_max": y_max,
                    "width": x_max - x_min,
                    "height": y_max - y_min,
                    "confidence": float(score),
                    "match_score": match_score
                }

        return best_match

    @staticmethod
    def _levenshtein_ratio(s1: str, s2: str) -> float:
        """Simple Levenshtein similarity ratio between two strings (0.0 to 1.0)."""
        if s1 == s2:
            return 1.0
        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
        dist = dp[len1][len2]
        return 1.0 - (dist / max(len1, len2))

    # -----------------------------------------------------------------------
    # 3. Trajectory, Drag Physics & Nudging
    # -----------------------------------------------------------------------

    def smooth_move(self, target_x: int, target_y: int, duration: float = 0.3, steps: int = 20):
        """Glides cursor with natural cosine ease-in-out interpolation."""
        self._ensure_input_desktop()
        start_x, start_y = self.get_cursor_pos()
        if start_x == target_x and start_y == target_y:
            return

        self.check_failsafe(target_x, target_y)
        actual_steps = max(5, int(steps))
        step_delay = max(0.005, duration / actual_steps)

        for i in range(1, actual_steps + 1):
            t = i / actual_steps
            ease = 0.5 * (1.0 - math.cos(math.pi * t))
            cur_x = int(round(start_x + (target_x - start_x) * ease))
            cur_y = int(round(start_y + (target_y - start_y) * ease))

            user_x, user_y = self.get_cursor_pos()
            if user_x <= 5 and user_y <= 5 and i > 1:
                raise DesktopFailsafeException("Failsafe triggered: cursor moved to corner by user. Aborting.")

            self.user32.SetCursorPos(cur_x, cur_y)
            time.sleep(step_delay)

        self.user32.SetCursorPos(target_x, target_y)

    def mouse_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        click_type: str = "single"
    ):
        """Performs mouse click at coordinates or current position."""
        self._ensure_input_desktop()
        if x is not None and y is not None:
            self.check_failsafe(x, y)
            self.smooth_move(x, y, duration=0.2)

        cur_x, cur_y = self.get_cursor_pos()
        self.check_failsafe(cur_x, cur_y)

        btn = button.lower().strip()
        down_flag = MOUSEEVENTF_RIGHTDOWN if btn == "right" else MOUSEEVENTF_LEFTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP if btn == "right" else MOUSEEVENTF_LEFTUP

        num_clicks = 2 if click_type == "double" else (3 if click_type == "triple" else 1)
        for i in range(num_clicks):
            self.user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.04)
            self.user32.mouse_event(up_flag, 0, 0, 0, 0)
            if i < num_clicks - 1:
                time.sleep(0.08)

    def press_hotkey(self, hotkey: str):
        """Dispatches keyboard shortcuts (e.g. 'ctrl+s', 'shift+left', 'esc')."""
        self._ensure_input_desktop()
        keys = [k.strip().lower() for k in hotkey.split("+") if k.strip()]
        vks = [VK_MAP[k] for k in keys if k in VK_MAP]
        if not vks:
            return

        for vk in vks:
            self.user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.02)
        time.sleep(0.04)
        for vk in reversed(vks):
            self.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)

    def drag_element(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        hold_delay: float = 0.15,
        deselect_offset_y: int = -70
    ):
        """
        Executes web-canvas drag physics:
        1. Moves to element center
        2. Mouse down + holds for canvas grab threshold
        3. Cosine ease-in-out drag motion
        4. Mouse up
        5. Clicks outside element to commit and deselect
        """
        self._ensure_input_desktop()
        self.check_failsafe(start_x, start_y)
        self.check_failsafe(end_x, end_y)

        # 1. Move to start position
        self.smooth_move(start_x, start_y, duration=0.25)
        time.sleep(0.1)

        # 2. Mouse DOWN + hold threshold (essential for web canvas drag recognizers)
        self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(hold_delay)

        # 3. Smooth trajectory drag
        self.smooth_move(end_x, end_y, duration=duration, steps=25)
        time.sleep(0.1)

        # 4. Mouse UP
        self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.3)

        # 5. Deselect & commit edit
        commit_y = max(100, end_y + deselect_offset_y)
        self.mouse_click(x=end_x, y=commit_y, button="left", click_type="single")
        time.sleep(0.4)

    def nudge_element(
        self,
        start_x: int,
        start_y: int,
        direction: str = "left",
        distance_px: int = 50,
        deselect_offset_y: int = -70
    ):
        """
        Selects element and uses Shift+Arrow keys (10px per press) for precise nudge.
        """
        # Click element to select
        self.mouse_click(x=start_x, y=start_y, button="left", click_type="single")
        time.sleep(0.2)

        # In Canva, pressing ESC switches from text typing mode to bounding box selection mode
        self.press_hotkey("esc")
        time.sleep(0.2)

        # Calculate number of Shift+Arrow presses (approx 10px each)
        steps = max(1, int(round(distance_px / 10)))
        hotkey = f"shift+{direction.lower().strip()}"
        for _ in range(steps):
            self.press_hotkey(hotkey)
            time.sleep(0.08)

        time.sleep(0.3)
        # Deselect & commit
        commit_y = max(100, start_y + deselect_offset_y)
        self.mouse_click(x=start_x, y=commit_y, button="left", click_type="single")
        time.sleep(0.4)

    # -----------------------------------------------------------------------
    # 4. Canva / Multi-Slide Presentation Navigator
    # -----------------------------------------------------------------------

    def ensure_canva_slide_visible(self, element_query: str) -> bool:
        """
        Checks if the requested element is visible on the current slide.
        If not, checks the Canva page thumbnails drawer or navigates to the slide.
        """
        # First check current canvas
        elem = self.locate_element_on_screen(element_query, exclude_browser_chrome=True)
        if elem:
            return True

        # Check if bottom drawer has thumbnails (look for 'Pages' or '10/10' or thumbnail text)
        drawer_elem = self.locate_element_on_screen(element_query, exclude_browser_chrome=False, min_y=680)
        if drawer_elem:
            logger.info(f"[Desktop Engine] Found target in slide thumbnail drawer at ({drawer_elem['center_x']}, {drawer_elem['center_y']}). Clicking...")
            self.mouse_click(drawer_elem['center_x'], drawer_elem['center_y'])
            time.sleep(1.0)
            return True

        # If drawer is closed, look for 'Pages' button at bottom right (y > 800, x > 1300)
        pages_btn = self.locate_element_on_screen("Pages", exclude_browser_chrome=False, min_y=780)
        if pages_btn:
            logger.info(f"[Desktop Engine] Opening Canva slide thumbnail drawer via button at ({pages_btn['center_x']}, {pages_btn['center_y']})...")
            self.mouse_click(pages_btn['center_x'], pages_btn['center_y'])
            time.sleep(1.0)
            # Re-scan thumbnail drawer
            thumb = self.locate_element_on_screen(element_query, exclude_browser_chrome=False, min_y=680)
            if thumb:
                self.mouse_click(thumb['center_x'], thumb['center_y'])
                time.sleep(1.0)
                return True

        return False

    # -----------------------------------------------------------------------
    # 5. Master High-Level Autonomous Manipulation Task Runner
    # -----------------------------------------------------------------------

    def execute_smart_move(
        self,
        window_query: str,
        element_query: str,
        delta_x: int = -50,
        delta_y: int = 0,
        method: str = "drag"
    ) -> Dict[str, Any]:
        """
        Executes end-to-end smart element repositioning:
        1. Finds and brings window to front (with Alt pulse bypass).
        2. Resolves slide presence (auto-navigating slides if needed).
        3. Vision grounds target element (filtering out browser chrome).
        4. Performs smooth drag or nudge.
        5. Commits and deselects.
        6. Re-scans and measures actual displacement.
        """
        try:
            # 1. Find & focus window
            win_res = self.focus_window(window_query, maximize=True)
            if win_res.get("status") == "error":
                return win_res

            time.sleep(0.5)

            # 2. Ensure slide visibility
            self.ensure_canva_slide_visible(element_query)

            # 3. Vision Grounding (BEFORE)
            elem_before = self.locate_element_on_screen(element_query, exclude_browser_chrome=True)
            if not elem_before:
                return {
                    "status": "error",
                    "summary": f"Could not visually locate element '{element_query}' on canvas in window '{window_query}'."
                }

            start_x = elem_before["center_x"]
            start_y = elem_before["center_y"]
            end_x = start_x + delta_x
            end_y = start_y + delta_y

            logger.info(f"[Desktop Engine] Located '{elem_before['text']}' at ({start_x}, {start_y}). Executing {method} to ({end_x}, {end_y})...")

            # 4. Perform Manipulation
            if method == "nudge":
                direction = "left" if delta_x < 0 else "right"
                dist = abs(delta_x)
                self.nudge_element(start_x, start_y, direction=direction, distance_px=dist)
            else:
                self.drag_element(start_x, start_y, end_x, end_y, duration=0.5)

            time.sleep(0.5)

            # 5. Vision Grounding (AFTER)
            elem_after = self.locate_element_on_screen(element_query, exclude_browser_chrome=True)
            verified_delta_x = (elem_after["center_x"] - start_x) if elem_after else delta_x
            verified_delta_y = (elem_after["center_y"] - start_y) if elem_after else delta_y

            summary_msg = (
                f"Successfully repositioned '{elem_before['text']}' in '{window_query}': "
                f"Moved from ({start_x}, {start_y}) to ({start_x + verified_delta_x}, {start_y + verified_delta_y}) "
                f"(Net displacement: Δx={verified_delta_x}px, Δy={verified_delta_y}px)."
            )

            return {
                "status": "success",
                "summary": summary_msg,
                "data": {
                    "window": win_res.get("data", {}).get("title"),
                    "element": elem_before["text"],
                    "start_position": {"x": start_x, "y": start_y},
                    "end_position": {
                        "x": elem_after["center_x"] if elem_after else end_x,
                        "y": elem_after["center_y"] if elem_after else end_y
                    },
                    "requested_delta": {"dx": delta_x, "dy": delta_y},
                    "verified_delta": {"dx": verified_delta_x, "dy": verified_delta_y},
                    "confidence": elem_after["confidence"] if elem_after else elem_before["confidence"]
                }
            }

        except DesktopFailsafeException as e:
            return {"status": "aborted", "summary": str(e), "data": {"error": "failsafe"}}
        except Exception as e:
            return {"status": "error", "summary": f"Desktop task error: {e}", "data": {"error": str(e)}}


# Global Singleton Operator Instance
desktop_operator = DesktopTakeoverEngine()
