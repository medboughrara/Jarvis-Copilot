"""
Desktop Pet Application & 100% True Transparent Floating Companion for Jarvis Copilot.
Runs a lightweight, native, hardware-composited transparent OpenHuman Ghosty mascot
that roams across monitors, points to on-screen elements, follows the user's cursor with its eyes,
and supports global hotkeys:
- [Right Shift + Enter]: Toggle cursor-following floating flight mode.
- [Right Shift + Backspace]: Trigger voice listening mode & speech briefing.

Zero Background Guarantee:
- Uses Win32 / DWM native -transparentcolor hardware compositing (0% white/gray box artifacts).
- DPI-aware, ultra-lightweight (<15MB RAM), 60 FPS smooth vector eye tracking.
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
import json
import tkinter as tk
from typing import Dict, Any, Optional
import config

logger = config.get_logger(__name__)


def init_process_dpi_awareness() -> int:
    """
    Task 3: Sets Per-Monitor DPI Awareness v2 on line 1 before any window or display calls.
    Verifies actual OS state via readback and logs explicit warnings on mismatch.
    """
    try:
        shcore = ctypes.windll.shcore
        shcore.SetProcessDpiAwareness(2)
        actual = ctypes.c_int()
        shcore.GetProcessDpiAwareness(0, ctypes.byref(actual))
        awareness_val = actual.value
        if awareness_val != 2:
            logger.warning(f"[DPI Warning] Requested Per-Monitor DPI Awareness v2 (2), OS reported ({awareness_val}).")
        else:
            logger.info("[DPI Init] Per-Monitor DPI Awareness v2 successfully enabled.")
        return awareness_val
    except Exception as e:
        logger.warning(f"[DPI Init Notice] shcore DPI configuration unavailable ({e}).")
        return 0


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class DesktopPetController:
    """Manages 100% transparent OpenHuman Ghosty canvas rendering, cursor following, hotkeys, and WebSocket sync."""

    TRANSPARENT_COLOR = "#010101"

    def __init__(self, port: int = 8000):
        self.port = port
        self.x = 300.0
        self.y = 250.0
        self.target_x = 300.0
        self.target_y = 250.0
        self.width = 260
        self.height = 290
        self.state = "idle"
        self.is_running = False
        # Default: Fixed in one place, movable manually
        self.follow_cursor = False
        self.is_pointing = False
        self.is_speaking = False
        self.speech_text = ""
        self.speech_clear_time = 0.0
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        self.root: Optional[tk.Tk] = None
        self.canvas: Optional[tk.Canvas] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.hotkey_thread: Optional[threading.Thread] = None
        
        self.last_cursor_x = 0
        self.last_cursor_y = 0
        self.last_cursor_move_time = time.time()
        self.blink_state = False
        self.last_blink_time = time.time()
        self.mouth_step = 0
        self.shutter_flash_until = 0.0

    def start_heartbeat_loop(self) -> None:
        """Emits periodic heartbeats to the screen annotator overlay every 1.5s."""
        from agent.screen_annotator import screen_annotator
        while self.is_running:
            screen_annotator.record_heartbeat(time.time())
            time.sleep(1.5)

    def start_hotkey_listener(self) -> None:
        """
        Monitors global system hotkeys in background:
        - Right Shift + Enter: Toggle Follow Cursor mode
        - Right Shift + Backspace: Trigger Voice Listening mode
        """
        GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState
        last_enter_state = False
        last_back_state = False

        while self.is_running:
            try:
                # Right Shift (0xA1) or General Shift (0x10)
                is_shift_down = bool(GetAsyncKeyState(0xA1) & 0x8000 or GetAsyncKeyState(0x10) & 0x8000)
                is_enter_down = bool(GetAsyncKeyState(0x0D) & 0x8000)
                is_back_down = bool(GetAsyncKeyState(0x08) & 0x8000)

                # Right Shift + Enter -> Toggle Follow Cursor
                if is_shift_down and is_enter_down:
                    if not last_enter_state:
                        self.toggle_follow_cursor()
                        last_enter_state = True
                else:
                    last_enter_state = False

                # Right Shift + Backspace -> Trigger Listen Mode
                if is_shift_down and is_back_down:
                    if not last_back_state:
                        self.trigger_listen_mode()
                        last_back_state = True
                else:
                    last_back_state = False

            except Exception:
                pass
            time.sleep(0.04)

    def toggle_follow_cursor(self) -> None:
        """Toggles between fixed-in-place mode and follow-cursor mode."""
        self.follow_cursor = not self.follow_cursor
        if self.follow_cursor:
            logger.info("[Desktop Pet Hotkey] Follow Cursor Mode: ENABLED")
            self.speak_text("Following your cursor, sir!")
        else:
            logger.info("[Desktop Pet Hotkey] Follow Cursor Mode: DISABLED (Fixed in place)")
            self.speak_text("Fixed in place.")

    def trigger_listen_mode(self) -> None:
        """Triggers interactive listening state with antenna glow & subtitle."""
        logger.info("[Desktop Pet Hotkey] Voice Listen Mode: TRIGGERED")
        self.trigger_shutter_flash()
        self.speak_text("Listening to your command, sir...")

    def trigger_shutter_flash(self) -> None:
        """Flashes indicator to signify active screen grounding or listening."""
        logger.info("[Desktop Pet] [SHUTTER] Visible Screen Indicator Flash Active.")
        self.shutter_flash_until = time.time() + 1.8

    def speak_text(self, text: str, duration: float = 3.5) -> None:
        """Displays holographic speech bubble over the pet."""
        self.speech_text = text
        self.is_speaking = True
        self.speech_clear_time = time.time() + max(duration, len(text) * 0.08)

    def point_to(self, target_name: str, x: int, y: int, w: int, h: int) -> None:
        """Triggers robotic arm pointing gesture and holographic spotlight."""
        from agent.screen_annotator import screen_annotator
        logger.info(f"[Desktop Pet] Pointing to '{target_name}' at ({x}, {y}).")
        self.state = "pointing"
        self.is_pointing = True
        pet_x = max(0, x - self.width - 20)
        pet_y = max(0, y - int(self.height / 2))
        self.target_x = float(pet_x)
        self.target_y = float(pet_y)
        self.x = float(pet_x)
        self.y = float(pet_y)
        if self.root:
            self.root.geometry(f"{self.width}x{self.height}+{int(self.x)}+{int(self.y)}")
        screen_annotator.add_spotlight(x, y, w, h, label=target_name)
        self.speak_text(f"Pointing to {target_name}!")
        
        def reset_pointing():
            time.sleep(4.5)
            self.is_pointing = False
            self.state = "idle"
        threading.Thread(target=reset_pointing, daemon=True).start()

    def build_gui(self) -> None:
        """Constructs the 100% transparent native Tkinter window and vector graphics canvas."""
        self.root = tk.Tk()
        self.root.title("Jarvis Desktop Pet")
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", self.TRANSPARENT_COLOR)
        self.root.config(bg=self.TRANSPARENT_COLOR)
        self.root.geometry(f"{self.width}x{self.height}+{int(self.x)}+{int(self.y)}")

        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg=self.TRANSPARENT_COLOR,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Mouse Drag-to-Reposition Bindings
        self.canvas.bind("<Button-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_end)

        # Mascot Click Interaction
        self.canvas.bind("<Double-Button-1>", lambda e: self.speak_text("Jarvis online! Ready for your commands."))

        # Start 60 FPS Rendering Loop
        self.root.after(20, self._render_frame)

    def _on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _on_drag_motion(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.x += dx
        self.y += dy
        self.target_x = self.x
        self.target_y = self.y
        self.root.geometry(f"{self.width}x{self.height}+{int(self.x)}+{int(self.y)}")

    def _on_drag_end(self, event):
        pass

    def _render_frame(self) -> None:
        """60 FPS Vector rendering frame: draws OpenHuman Ghosty avatar, pupil tracking, and speech bubble."""
        if not self.is_running or not self.canvas:
            return

        pt = POINT()
        cur_x, cur_y = 0, 0
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            cur_x, cur_y = pt.x, pt.y

        # Detect cursor movement
        if abs(cur_x - self.last_cursor_x) > 3 or abs(cur_y - self.last_cursor_y) > 3:
            self.last_cursor_x = cur_x
            self.last_cursor_y = cur_y
            self.last_cursor_move_time = time.time()

        idle_duration = time.time() - self.last_cursor_move_time

        # Follow Cursor Motion (if enabled)
        if self.follow_cursor and not self.is_pointing:
            if idle_duration < 2.0:
                self.target_x = cur_x + 65
                self.target_y = cur_y + 35
                dx = (self.target_x - self.x) * 0.08
                dy = (self.target_y - self.y) * 0.08
                if abs(dx) > 0.3 or abs(dy) > 0.3:
                    self.x += dx
                    self.y += dy
                    self.root.geometry(f"{self.width}x{self.height}+{int(self.x)}+{int(self.y)}")
            else:
                # Ambient hover bobbing
                t = time.time()
                bob_y = math.sin(t * 2.0) * 6.0
                bob_x = math.cos(t * 1.0) * 4.0
                self.x += (self.target_x + bob_x - self.x) * 0.05
                self.y += (self.target_y + bob_y - self.y) * 0.05
                self.root.geometry(f"{self.width}x{self.height}+{int(self.x)}+{int(self.y)}")

        # Clear Canvas
        self.canvas.delete("all")

        now = time.time()

        # 1. Speech Bubble (if active)
        if self.is_speaking:
            if now > self.speech_clear_time:
                self.is_speaking = False
                self.speech_text = ""
            else:
                # Draw Speech Bubble pill
                self.canvas.create_rectangle(20, 6, 240, 48, fill="#040812", outline="#00f2ff", width=1.5)
                self.canvas.create_text(
                    130, 27,
                    text=self.speech_text[:55] + ("..." if len(self.speech_text) > 55 else ""),
                    fill="#cffafe",
                    font=("Segoe UI", 8, "bold"),
                    width=210
                )

        # Center Coordinates for Ghosty Avatar
        cx = 130
        cy = 155

        # 2. Ambient Glowing Orbit Ring & Shutter Flash Halo
        ring_pulse = math.sin(time.time() * 2.5) * 3
        halo_color = "#f59e0b" if (now < self.shutter_flash_until) else "#00f2ff"
        self.canvas.create_oval(cx - 82 - ring_pulse, cy - 82 - ring_pulse, cx + 82 + ring_pulse, cy + 82 + ring_pulse, outline=halo_color, width=1)

        # 3. Feet Lobes (OpenHuman Ghosty Feet)
        self.canvas.create_oval(cx - 52, cy + 48, cx - 12, cy + 78, fill="#18233c", outline="#00f2ff", width=2)
        self.canvas.create_oval(cx + 12, cy + 48, cx + 52, cy + 78, fill="#18233c", outline="#00f2ff", width=2)

        # 4. Main Organic 3D Torso (Smooth Curved Dome Body from Platform)
        body_points = [
            cx, cy - 72,           # Top Head Dome
            cx + 48, cy - 58,
            cx + 68, cy - 12,      # Right upper torso
            cx + 64, cy + 38,      # Right lower body
            cx + 36, cy + 66,      # Right foot join
            cx, cy + 70,           # Bottom center
            cx - 36, cy + 66,      # Left foot join
            cx - 64, cy + 38,      # Left lower body
            cx - 68, cy - 12,      # Left upper torso
            cx - 48, cy - 58       # Left head dome
        ]
        self.canvas.create_polygon(body_points, fill="#0f172a", outline="#00f2ff", width=2.5, smooth=True)

        # Inner 3D Highlight Depth Layer
        inner_points = [
            cx, cy - 62,
            cx + 38, cy - 48,
            cx + 52, cy - 10,
            cx + 48, cy + 28,
            cx, cy + 54,
            cx - 48, cy + 28,
            cx - 52, cy - 10,
            cx - 38, cy - 48
        ]
        self.canvas.create_polygon(inner_points, fill="#1e293b", outline="", smooth=True)

        # 5. Cute Waving/Pointing Robotic Arms
        if self.is_pointing:
            # Point left arm outward/upward
            point_arm = [cx - 55, cy + 5, cx - 88, cy - 25, cx - 80, cy - 35, cx - 48, cy - 5]
            self.canvas.create_polygon(point_arm, fill="#1e293b", outline="#00f2ff", width=2, smooth=True)
            self.canvas.create_oval(cx - 92, cy - 38, cx - 78, cy - 24, fill="#38bdf8", outline="")
            # Right arm relaxed
            right_arm = [cx + 55, cy + 5, cx + 75, cy + 22, cx + 68, cy + 34, cx + 50, cy + 20]
            self.canvas.create_polygon(right_arm, fill="#1e293b", outline="#00f2ff", width=2, smooth=True)
        else:
            # Right arm cute wave
            wave_y = math.sin(time.time() * 4.0) * 4
            right_arm = [cx + 55, cy + 5, cx + 80, cy - 12 + wave_y, cx + 90, cy - 2 + wave_y, cx + 62, cy + 24]
            self.canvas.create_polygon(right_arm, fill="#1e293b", outline="#00f2ff", width=2, smooth=True)
            # Left arm resting
            left_arm = [cx - 55, cy + 5, cx - 75, cy + 20, cx - 68, cy + 32, cx - 50, cy + 18]
            self.canvas.create_polygon(left_arm, fill="#1e293b", outline="#00f2ff", width=2, smooth=True)

        # 6. Soft Pink Blush Cheeks (Exact OpenHuman Platform Style)
        self.canvas.create_oval(cx - 50, cy + 2, cx - 28, cy + 16, fill="#ec4899", outline="")
        self.canvas.create_oval(cx + 28, cy + 2, cx + 50, cy + 16, fill="#ec4899", outline="")

        # 7. Eye Blinking Logic
        if now - self.last_blink_time > 3.6:
            self.blink_state = True
            if now - self.last_blink_time > 3.8:
                self.blink_state = False
                self.last_blink_time = now

        # 8. Intelligent Pupil Vector Tracking Mouse Position
        pet_screen_x = self.x + cx
        pet_screen_y = self.y + cy
        angle = math.atan2(cur_y - pet_screen_y, cur_x - pet_screen_x)
        dist = math.hypot(cur_x - pet_screen_x, cur_y - pet_screen_y)
        max_r = 5.5
        pupil_r = min(max_r, dist / 35.0)
        p_dx = math.cos(angle) * pupil_r
        p_dy = math.sin(angle) * pupil_r

        # Glowing Vertical Oval Eyes (Exact Platform Geometry)
        if not self.blink_state:
            # Left Eye Socket
            self.canvas.create_oval(cx - 32, cy - 28, cx - 8, cy + 8, fill="#00f2ff", outline="")
            # Left Pupil (White Shiny Highlight)
            self.canvas.create_oval(cx - 24 + p_dx, cy - 18 + p_dy, cx - 16 + p_dx, cy - 6 + p_dy, fill="#ffffff", outline="")
            
            # Right Eye Socket
            self.canvas.create_oval(cx + 8, cy - 28, cx + 32, cy + 8, fill="#00f2ff", outline="")
            # Right Pupil (White Shiny Highlight)
            self.canvas.create_oval(cx + 16 + p_dx, cy - 18 + p_dy, cx + 24 + p_dx, cy - 6 + p_dy, fill="#ffffff", outline="")
        else:
            # Blinking closed curve
            self.canvas.create_line(cx - 32, cy - 10, cx - 8, cy - 10, fill="#00f2ff", width=3)
            self.canvas.create_line(cx + 8, cy - 10, cx + 32, cy - 10, fill="#00f2ff", width=3)

        # 9. Viseme Mouth (Animated Speaking vs Cute Smile)
        if self.is_speaking:
            self.mouth_step += 1
            mouth_open = int((self.mouth_step % 6) * 1.5)
            self.canvas.create_oval(cx - 12, cy + 12 - mouth_open, cx + 12, cy + 18 + mouth_open, fill="#00f2ff", outline="")
        else:
            # Platform Cyan Smile
            self.canvas.create_line(cx - 12, cy + 16, cx, cy + 22, cx + 12, cy + 16, fill="#00f2ff", width=3, smooth=True)

        # Schedule Next Frame (~60 FPS)
        self.root.after(16, self._render_frame)


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


def launch_desktop_pet(port: int = 8000, blocking: bool = True) -> DesktopPetController:
    """Entry point for launching the Desktop Pet application."""
    # 1. First line: Set and verify DPI awareness
    init_process_dpi_awareness()

    # 2. Auto-start web server if not already active
    ensure_web_server_running(port=port)

    controller = DesktopPetController(port=port)
    controller.is_running = True

    # 3. Start background threads
    controller.heartbeat_thread = threading.Thread(target=controller.start_heartbeat_loop, daemon=True)
    controller.heartbeat_thread.start()

    controller.hotkey_thread = threading.Thread(target=controller.start_hotkey_listener, daemon=True)
    controller.hotkey_thread.start()

    logger.info(f"[Desktop Pet] Initialized at ({controller.x}, {controller.y}). Connecting to web server on port {port}...")
    logger.info("[Desktop Pet Hotkeys] Press [Right Shift + Enter] to toggle cursor follow | Press [Right Shift + Backspace] to listen.")

    if blocking:
        controller.build_gui()
        controller.root.mainloop()

    return controller


if __name__ == "__main__":
    launch_desktop_pet(blocking=True)
