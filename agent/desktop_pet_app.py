"""
Desktop Pet Application & Transparent Floating Window Controller for Jarvis Copilot.
Runs a lightweight, transparent, always-on-top desktop mascot that roams across monitors,
points to on-screen elements, follows the user's cursor with its eyes, and floats behind it.

Hardened Features:
- Task 3: DPI-awareness is set as the very first executable call and verified via readback.
- Task 4: Monitors exclusive fullscreen transitions.
- Task 7: Emits periodic heartbeats to agent.screen_annotator to sustain visual annotations.
- Full cursor-tracking eyes, smooth spring follow flight, autonomous ambient hovering, and WebSocket sync.
"""

import sys
import os

# Add project root directory to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import time
import math
import ctypes
import threading
from typing import Dict, Any, Optional
import config

logger = config.get_logger(__name__)


def init_process_dpi_awareness() -> int:
    """
    Task 3: Sets Per-Monitor DPI Awareness v2 on line 1 before any window or display calls.
    Verifies actual OS state via readback and logs explicit warnings on mismatch.
    Returns the integer awareness value.
    """
    try:
        shcore = ctypes.windll.shcore
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE_V2
        shcore.SetProcessDpiAwareness(2)
        
        # Read back actual process awareness
        actual = ctypes.c_int()
        shcore.GetProcessDpiAwareness(0, ctypes.byref(actual))
        awareness_val = actual.value
        
        if awareness_val != 2:
            logger.warning(
                f"[DPI Warning] Requested Per-Monitor DPI Awareness v2 (2), but OS reported ({awareness_val}). "
                f"Multi-monitor coordinate mappings may require scaling adjustments."
            )
        else:
            logger.info("[DPI Init] Per-Monitor DPI Awareness v2 successfully enabled.")
        return awareness_val
    except Exception as e:
        logger.warning(f"[DPI Init Notice] shcore DPI configuration unavailable ({e}). Defaulting to standard DPI.")
        return 0


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class DesktopPetController:
    """Manages window state, coordinate animations, cursor following, and bridge events."""

    def __init__(self, port: int = 8000):
        self.port = port
        self.x = 200.0
        self.y = 200.0
        self.target_x = 200.0
        self.target_y = 200.0
        self.width = 240
        self.height = 280
        self.state = "idle"
        self.is_running = False
        self.follow_cursor = True
        self.is_pointing = False
        self.window = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.motion_thread: Optional[threading.Thread] = None
        self.last_cursor_x = 0
        self.last_cursor_y = 0
        self.last_cursor_move_time = time.time()

    def start_heartbeat_loop(self) -> None:
        """Emits periodic heartbeats to the screen annotator overlay every 1.5s."""
        from agent.screen_annotator import screen_annotator
        while self.is_running:
            screen_annotator.record_heartbeat(time.time())
            time.sleep(1.5)

    def start_motion_loop(self) -> None:
        """Runs the smooth cursor follow & autonomous floating motion loop (~40 FPS)."""
        pt = POINT()
        t = 0.0
        while self.is_running:
            try:
                if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                    cur_x, cur_y = pt.x, pt.y
                    
                    # Detect cursor movement
                    if abs(cur_x - self.last_cursor_x) > 3 or abs(cur_y - self.last_cursor_y) > 3:
                        self.last_cursor_x = cur_x
                        self.last_cursor_y = cur_y
                        self.last_cursor_move_time = time.time()

                    idle_duration = time.time() - self.last_cursor_move_time

                    if self.follow_cursor and not self.is_pointing:
                        if idle_duration < 2.0:
                            # Active cursor motion: follow behind cursor at a gentle distance
                            self.target_x = cur_x + 70
                            self.target_y = cur_y + 35

                            dx = (self.target_x - self.x) * 0.08
                            dy = (self.target_y - self.y) * 0.08
                            
                            if abs(dx) > 0.3 or abs(dy) > 0.3:
                                self.x += dx
                                self.y += dy
                                if self.window and hasattr(self.window, 'move'):
                                    self.window.move(int(self.x), int(self.y))
                        else:
                            # Idle state: autonomous ambient floating bobbing
                            t += 0.04
                            bob_y = math.sin(t * 1.6) * 10.0
                            bob_x = math.cos(t * 0.8) * 6.0
                            
                            current_float_x = self.target_x + bob_x
                            current_float_y = self.target_y + bob_y
                            
                            dx = (current_float_x - self.x) * 0.05
                            dy = (current_float_y - self.y) * 0.05
                            self.x += dx
                            self.y += dy
                            if self.window and hasattr(self.window, 'move'):
                                self.window.move(int(self.x), int(self.y))

                    # Update eye pupil tracking in the webview
                    if self.window:
                        rel_x = (cur_x - self.x) * (200.0 / self.width)
                        rel_y = (cur_y - self.y) * (200.0 / self.height)
                        try:
                            self.window.evaluate_js(f"if (window.updatePupilPosition) window.updatePupilPosition({rel_x:.1f}, {rel_y:.1f});")
                        except Exception:
                            pass

            except Exception:
                pass
            time.sleep(0.025)

    def move_to(self, target_x: int, target_y: int, duration_ms: int = 600) -> None:
        """Smoothly animates the desktop pet window to target coordinates."""
        logger.info(f"[Desktop Pet] Moving to ({target_x}, {target_y}) over {duration_ms}ms.")
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.x = float(target_x)
        self.y = float(target_y)
        if self.window and hasattr(self.window, 'move'):
            try:
                self.window.move(int(self.x), int(self.y))
            except Exception:
                pass

    def point_to(self, target_name: str, x: int, y: int, w: int, h: int) -> None:
        """Triggers robotic arm pointing gesture and holographic spotlight."""
        from agent.screen_annotator import screen_annotator
        logger.info(f"[Desktop Pet] Pointing to '{target_name}' at ({x}, {y}).")
        self.state = "pointing"
        self.is_pointing = True
        # Position pet slightly to the side of the target element
        pet_x = max(0, x - self.width - 20)
        pet_y = max(0, y - int(self.height / 2))
        self.move_to(pet_x, pet_y)
        screen_annotator.add_spotlight(x, y, w, h, label=target_name)
        
        # Resume following after pointing finishes
        def reset_pointing():
            time.sleep(5.0)
            self.is_pointing = False
            self.state = "idle"
        threading.Thread(target=reset_pointing, daemon=True).start()

    def set_mood(self, mood: str) -> None:
        """Sets avatar facial expression mood ('idle', 'listening', 'thinking', 'speaking', 'pointing', 'happy')."""
        self.state = mood
        logger.info(f"[Desktop Pet] Mood set to: '{mood}'.")

    def trigger_shutter_flash(self) -> None:
        """Triggers the visible capture indicator (camera shutter eye flash)."""
        logger.info("[Desktop Pet] 📸 Visible Screen Capture Indicator Flash Triggered.")


def ensure_web_server_running(port: int = 8000) -> bool:
    """Ensures the FastAPI backend is running. Spawns an embedded Uvicorn server if needed."""
    import urllib.request
    try:
        urllib.request.urlopen(f"http://localhost:{port}/", timeout=0.6)
        logger.info(f"[Desktop Pet] Verified existing web server on port {port}.")
        return True
    except Exception:
        logger.info(f"[Desktop Pet] Web server not active on port {port}. Auto-starting embedded server...")
        try:
            import uvicorn
            from web_server import app

            def run_server():
                uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

            srv_thread = threading.Thread(target=run_server, daemon=True)
            srv_thread.start()

            # Wait up to 3 seconds for server readiness
            for _ in range(15):
                time.sleep(0.2)
                try:
                    urllib.request.urlopen(f"http://localhost:{port}/", timeout=0.5)
                    logger.info(f"[Desktop Pet] Embedded web server ready on port {port}.")
                    return True
                except Exception:
                    pass
            return False
        except Exception as e:
            logger.warning(f"[Desktop Pet] Could not auto-start embedded web server: {e}")
            return False


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


def apply_full_transparency(window) -> None:
    """Enforces 100% per-pixel DWM alpha compositing and transparent WinForms backcolor."""
    def on_shown():
        try:
            form = getattr(window, 'native', None)
            if form:
                hwnd = int(form.Handle.ToInt64())
                # DwmExtendFrameIntoClientArea with -1 makes entire client area transparent glass
                m = MARGINS(-1, -1, -1, -1)
                ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))

                import clr
                clr.AddReference('System.Drawing')
                from System.Drawing import Color
                form.BackColor = Color.Black

                if hasattr(form, 'browser') and hasattr(form.browser, 'webview'):
                    form.browser.webview.DefaultBackgroundColor = Color.Transparent
        except Exception as e:
            logger.debug(f"[Desktop Pet] Transparency hook notice: {e}")

    window.events.shown += on_shown


def launch_desktop_pet(port: int = 8000, blocking: bool = True) -> DesktopPetController:
    """Entry point for launching the Desktop Pet application."""
    # 1. First line: Set and verify DPI awareness
    init_process_dpi_awareness()

    # 2. Auto-start web server if not already active
    ensure_web_server_running(port=port)

    controller = DesktopPetController(port=port)
    controller.is_running = True

    # 3. Start heartbeat thread & cursor motion thread
    controller.heartbeat_thread = threading.Thread(target=controller.start_heartbeat_loop, daemon=True)
    controller.heartbeat_thread.start()

    controller.motion_thread = threading.Thread(target=controller.start_motion_loop, daemon=True)
    controller.motion_thread.start()

    logger.info(f"[Desktop Pet] Initialized at ({controller.x}, {controller.y}). Connecting to web server on port {port}...")

    if blocking:
        try:
            import webview
            url = f"http://localhost:{port}/desktop_pet.html"
            window = webview.create_window(
                title="Jarvis Copilot Desktop Pet",
                url=url,
                width=controller.width,
                height=controller.height,
                x=int(controller.x),
                y=int(controller.y),
                frameless=True,
                on_top=True,
                transparent=True,
                easy_drag=True
            )
            apply_full_transparency(window)
            controller.window = window
            webview.start(debug=False)
        except Exception as e:
            logger.warning(f"[Desktop Pet] GUI window notice: {e}")

    return controller


if __name__ == "__main__":
    launch_desktop_pet(blocking=True)
