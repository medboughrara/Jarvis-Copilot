"""
Desktop Automation, System Metrics, Cursor & Navigation Takeover Tool for Jarvis Copilot.
Provides full hands-on desktop takeover and monitor navigation:
- Real-time cursor coordinates and multi-monitor resolution enumeration
- Human-like smooth mouse motion interpolation (cosine ease-in-out)
- Mouse clicks (left, right, middle, single, double, triple)
- Mouse drag-and-drop operations across multi-monitor virtual desktop
- Mouse wheel scrolling (up, down, left, right)
- Unicode keystroke typing into active focus
- Hotkey and shortcut combination dispatch (Ctrl+S, Alt+Tab, Win+D, etc.)
- Autonomous Vision-to-Click element locator using RapidOCR local grounding
- System telemetry (CPU, RAM, Disk, Uptime) & Process enumeration
- Clipboard management (read/write)
- Built-in corner failsafe protection
"""

import os
import time
import math
import ctypes
from ctypes import wintypes
import subprocess
from typing import Dict, Any, List, Optional, Tuple
import psutil
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

SCRATCH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
os.makedirs(SCRATCH_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Native Win32 API Definitions & Structures
# ---------------------------------------------------------------------------

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class CursorFailsafeException(Exception):
    """Raised when mouse failsafe boundary is triggered (e.g. cursor jerked to screen corner)."""
    pass


# Mouse Event Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000
MOUSEEVENTF_ABSOLUTE = 0x8000
WHEEL_DELTA = 120

# Keyboard Event Constants
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# Virtual Key Mapping
VK_MAP = {
    # Modifiers
    "ctrl": 0x11, "control": 0x11, "lctrl": 0xA2, "rctrl": 0xA3,
    "shift": 0x10, "lshift": 0xA0, "rshift": 0xA1,
    "alt": 0x12, "menu": 0x12, "lalt": 0xA4, "ralt": 0xA5,
    "win": 0x5B, "windows": 0x5B, "super": 0x5B, "meta": 0x5B,
    # Navigation & Control
    "enter": 0x0D, "return": 0x0D,
    "esc": 0x1B, "escape": 0x1B,
    "tab": 0x09,
    "space": 0x20, "spacebar": 0x20,
    "backspace": 0x08, "bksp": 0x08,
    "delete": 0x2E, "del": 0x2E,
    "insert": 0x2D, "ins": 0x2D,
    "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pgup": 0x21,
    "pagedown": 0x22, "pgdn": 0x22,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "printscreen": 0x2C, "prtsc": 0x2C,
    "pause": 0x13, "capslock": 0x14,
    # Function Keys F1-F12
    **{f"f{i}": 0x70 + (i - 1) for i in range(1, 13)},
    # Letters A-Z
    **{chr(c).lower(): c for c in range(ord('A'), ord('Z') + 1)},
    # Digits 0-9
    **{str(i): ord('0') + i for i in range(10)},
}


def _ensure_input_desktop() -> bool:
    """
    Attaches the current calling thread to the interactive Windows input desktop.
    Ensures seamless execution even within subshell, IDE services, or background worker threads.
    """
    try:
        user32 = ctypes.windll.user32
        hDesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if hDesk:
            user32.SetThreadDesktop(hDesk)
            return True
    except Exception as e:
        logger.debug(f"[Desktop Control] OpenInputDesktop notice: {e}")
    return False


def _get_cursor_pos() -> Tuple[int, int]:
    """Retrieves current physical cursor position on desktop."""
    _ensure_input_desktop()
    pt = POINT()
    if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
        return int(pt.x), int(pt.y)
    return 0, 0


def _get_display_metrics() -> Dict[str, Any]:
    """Retrieves full display layout, primary monitor size, and virtual multi-monitor bounds."""
    _ensure_input_desktop()
    user32 = ctypes.windll.user32
    primary_w = user32.GetSystemMetrics(0)   # SM_CXSCREEN
    primary_h = user32.GetSystemMetrics(1)   # SM_CYSCREEN
    virt_x = user32.GetSystemMetrics(76)     # SM_XVIRTUALSCREEN
    virt_y = user32.GetSystemMetrics(77)     # SM_YVIRTUALSCREEN
    virt_w = user32.GetSystemMetrics(78)     # SM_CXVIRTUALSCREEN
    virt_h = user32.GetSystemMetrics(79)     # SM_CYVIRTUALSCREEN

    monitors = []
    try:
        def _cb(hMonitor, hdcMonitor, lprcMonitor, dwData):
            r = lprcMonitor.contents
            monitors.append({
                "left": int(r.left),
                "top": int(r.top),
                "right": int(r.right),
                "bottom": int(r.bottom),
                "width": int(r.right - r.left),
                "height": int(r.bottom - r.top)
            })
            return 1

        CB_TYPE = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wintypes.RECT), ctypes.c_void_p)
        cb = CB_TYPE(_cb)
        user32.EnumDisplayMonitors(None, None, cb, 0)
    except Exception as e:
        logger.debug(f"[Desktop Control] EnumDisplayMonitors fallback: {e}")

    if not monitors:
        monitors.append({
            "left": 0, "top": 0, "right": primary_w, "bottom": primary_h,
            "width": primary_w, "height": primary_h
        })

    cur_x, cur_y = _get_cursor_pos()

    return {
        "cursor": {"x": cur_x, "y": cur_y},
        "primary_monitor": {"width": primary_w, "height": primary_h},
        "virtual_desktop": {
            "x": virt_x, "y": virt_y, "width": virt_w, "height": virt_h,
            "monitors_count": len(monitors)
        },
        "monitors": monitors
    }


def _check_failsafe(x: int, y: int):
    """
    Emergency failsafe boundary check.
    If the cursor reaches (0, 0) or within 5px of the extreme top-left corner,
    takeover execution immediately halts to give human user complete physical control.
    """
    if x <= 5 and y <= 5:
        raise CursorFailsafeException("Failsafe triggered: cursor in top-left corner (0,0). Automation aborted.")


def _smooth_move(target_x: int, target_y: int, duration: float = 0.3, steps: int = 20):
    """
    Glides cursor smoothly from its current position to (target_x, target_y)
    using cosine ease-in-out interpolation for natural human-like motion.
    """
    _ensure_input_desktop()
    start_x, start_y = _get_cursor_pos()

    if start_x == target_x and start_y == target_y:
        return

    _check_failsafe(target_x, target_y)

    actual_steps = max(5, int(steps))
    step_delay = max(0.005, duration / actual_steps)

    for i in range(1, actual_steps + 1):
        t = i / actual_steps
        # Cosine ease-in-out curve
        ease = 0.5 * (1.0 - math.cos(math.pi * t))
        cur_x = int(round(start_x + (target_x - start_x) * ease))
        cur_y = int(round(start_y + (target_y - start_y) * ease))

        # Check if user physically intervened to corner during movement
        user_x, user_y = _get_cursor_pos()
        if user_x <= 5 and user_y <= 5 and i > 1:
            raise CursorFailsafeException("Failsafe triggered: cursor moved to corner by user. Aborting.")

        ctypes.windll.user32.SetCursorPos(cur_x, cur_y)
        time.sleep(step_delay)

    # Ensure precise final coordinate
    ctypes.windll.user32.SetCursorPos(target_x, target_y)


# ---------------------------------------------------------------------------
# LangChain Desktop Takeover & Cursor Navigation Tools
# ---------------------------------------------------------------------------

@tool
def get_cursor_position() -> Dict[str, Any]:
    """
    Returns the real-time (x, y) coordinates of the mouse cursor, primary monitor dimensions,
    and multi-monitor virtual desktop layout.
    """
    metrics = _get_display_metrics()
    cur = metrics["cursor"]
    return {
        "status": "success",
        "summary": f"Cursor at ({cur['x']}, {cur['y']}) on {len(metrics['monitors'])}-monitor desktop ({metrics['virtual_desktop']['width']}x{metrics['virtual_desktop']['height']}).",
        "data": metrics
    }


@tool
def mouse_move(x: int, y: int, smooth: bool = True, duration: float = 0.3) -> Dict[str, Any]:
    """
    Moves the mouse cursor to physical coordinate (x, y) on any connected monitor.
    
    Args:
        x: Horizontal pixel coordinate across the virtual desktop.
        y: Vertical pixel coordinate across the virtual desktop.
        smooth: If True, uses smooth cosine ease-in-out interpolation like a human hand.
        duration: Travel time in seconds when smooth=True (default 0.3s).
    """
    try:
        _ensure_input_desktop()
        _check_failsafe(x, y)
        if smooth:
            _smooth_move(x, y, duration=duration)
        else:
            ctypes.windll.user32.SetCursorPos(x, y)

        final_x, final_y = _get_cursor_pos()
        return {
            "status": "success",
            "summary": f"Mouse moved to ({final_x}, {final_y}) successfully.",
            "data": {"x": final_x, "y": final_y}
        }
    except CursorFailsafeException as e:
        return {"status": "aborted", "summary": str(e), "data": {"error": "failsafe"}}
    except Exception as e:
        return {"status": "error", "summary": f"Failed to move mouse: {e}", "data": {"error": str(e)}}


@tool
def mouse_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    click_type: str = "single"
) -> Dict[str, Any]:
    """
    Performs a mouse click at target coordinates (or current cursor position).
    
    Args:
        x: Optional horizontal coordinate. If provided, cursor moves there before clicking.
        y: Optional vertical coordinate. If provided, cursor moves there before clicking.
        button: 'left', 'right', or 'middle' (default 'left').
        click_type: 'single', 'double', or 'triple' (default 'single').
    """
    try:
        _ensure_input_desktop()
        if x is not None and y is not None:
            _check_failsafe(x, y)
            _smooth_move(x, y, duration=0.25)

        cur_x, cur_y = _get_cursor_pos()
        _check_failsafe(cur_x, cur_y)

        btn = button.lower().strip()
        if btn == "right":
            down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        elif btn == "middle":
            down_flag, up_flag = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
        else:
            down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

        num_clicks = 1
        if click_type == "double":
            num_clicks = 2
        elif click_type == "triple":
            num_clicks = 3

        user32 = ctypes.windll.user32
        for click_idx in range(num_clicks):
            user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.04)
            user32.mouse_event(up_flag, 0, 0, 0, 0)
            if click_idx < num_clicks - 1:
                time.sleep(0.08)

        return {
            "status": "success",
            "summary": f"{click_type.capitalize()} {btn}-click executed at ({cur_x}, {cur_y}).",
            "data": {"x": cur_x, "y": cur_y, "button": btn, "click_type": click_type}
        }
    except CursorFailsafeException as e:
        return {"status": "aborted", "summary": str(e), "data": {"error": "failsafe"}}
    except Exception as e:
        return {"status": "error", "summary": f"Failed to execute click: {e}", "data": {"error": str(e)}}


@tool
def mouse_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float = 0.5,
    button: str = "left"
) -> Dict[str, Any]:
    """
    Drags the mouse from (start_x, start_y) to (end_x, end_y) with the mouse button pressed.
    
    Args:
        start_x: Starting horizontal coordinate.
        start_y: Starting vertical coordinate.
        end_x: Target release horizontal coordinate.
        end_y: Target release vertical coordinate.
        duration: Drag travel duration in seconds.
        button: 'left' or 'right' (default 'left').
    """
    try:
        _ensure_input_desktop()
        _check_failsafe(start_x, start_y)
        _check_failsafe(end_x, end_y)

        # Move to start
        _smooth_move(start_x, start_y, duration=0.25)
        time.sleep(0.05)

        btn = button.lower().strip()
        down_flag = MOUSEEVENTF_RIGHTDOWN if btn == "right" else MOUSEEVENTF_LEFTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP if btn == "right" else MOUSEEVENTF_LEFTUP

        user32 = ctypes.windll.user32
        user32.mouse_event(down_flag, 0, 0, 0, 0)
        time.sleep(0.05)

        # Smooth drag to destination
        _smooth_move(end_x, end_y, duration=duration)
        time.sleep(0.05)

        user32.mouse_event(up_flag, 0, 0, 0, 0)
        time.sleep(0.02)

        return {
            "status": "success",
            "summary": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y}) with {btn} button.",
            "data": {"start": [start_x, start_y], "end": [end_x, end_y], "button": btn}
        }
    except CursorFailsafeException as e:
        # Guarantee release of mouse button on abort
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP | MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        return {"status": "aborted", "summary": str(e), "data": {"error": "failsafe"}}
    except Exception as e:
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP | MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        return {"status": "error", "summary": f"Failed to drag: {e}", "data": {"error": str(e)}}


@tool
def mouse_scroll(
    clicks: int = 3,
    direction: str = "down",
    x: Optional[int] = None,
    y: Optional[int] = None
) -> Dict[str, Any]:
    """
    Scrolls the mouse wheel up, down, left, or right.
    
    Args:
        clicks: Number of scroll notches / wheel ticks (default 3).
        direction: 'up', 'down', 'left', or 'right' (default 'down').
        x: Optional coordinate to move before scrolling.
        y: Optional coordinate to move before scrolling.
    """
    try:
        _ensure_input_desktop()
        if x is not None and y is not None:
            _smooth_move(x, y, duration=0.2)

        dir_clean = direction.lower().strip()
        delta = WHEEL_DELTA * clicks

        user32 = ctypes.windll.user32
        if dir_clean == "up":
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        elif dir_clean == "down":
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -delta, 0)
        elif dir_clean == "right":
            user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, delta, 0)
        elif dir_clean == "left":
            user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, -delta, 0)
        else:
            return {"status": "error", "summary": f"Unknown scroll direction '{direction}'. Use 'up', 'down', 'left', or 'right'."}

        return {
            "status": "success",
            "summary": f"Scrolled {direction} by {clicks} click(s).",
            "data": {"clicks": clicks, "direction": dir_clean}
        }
    except Exception as e:
        return {"status": "error", "summary": f"Failed to scroll: {e}", "data": {"error": str(e)}}


@tool
def type_text(text: str, press_enter: bool = False, delay: float = 0.01) -> Dict[str, Any]:
    """
    Types text into the currently focused window or field using native Unicode keystroke injection.
    Preserves casing, punctuation, symbols, and international characters.
    
    Args:
        text: The text string to type.
        press_enter: If True, sends an Enter keypress after typing.
        delay: Delay in seconds between keystrokes (default 0.01s).
    """
    if not text:
        return {"status": "error", "summary": "Text cannot be empty."}

    try:
        _ensure_input_desktop()
        user32 = ctypes.windll.user32

        for char in text:
            # Send character as Unicode key event
            user32.keybd_event(0, ord(char), KEYEVENTF_UNICODE, 0)
            user32.keybd_event(0, ord(char), KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
            if delay > 0:
                time.sleep(delay)

        if press_enter:
            time.sleep(0.05)
            vk_enter = VK_MAP["enter"]
            user32.keybd_event(vk_enter, 0, 0, 0)
            user32.keybd_event(vk_enter, 0, KEYEVENTF_KEYUP, 0)

        return {
            "status": "success",
            "summary": f"Typed {len(text)} characters into active focus (enter={press_enter}).",
            "data": {"length": len(text), "press_enter": press_enter}
        }
    except Exception as e:
        return {"status": "error", "summary": f"Failed to type text: {e}", "data": {"error": str(e)}}


@tool
def press_hotkey(hotkey: str) -> Dict[str, Any]:
    """
    Presses a keyboard shortcut or key combination (e.g. 'ctrl+s', 'alt+tab', 'win+d', 'ctrl+shift+esc', 'enter').
    
    Args:
        hotkey: Combination string separated by '+' (e.g. 'ctrl+c', 'ctrl+v', 'alt+f4', 'win+r', 'esc').
    """
    if not hotkey:
        return {"status": "error", "summary": "Hotkey string cannot be empty."}

    try:
        _ensure_input_desktop()
        keys = [k.strip().lower() for k in hotkey.split("+") if k.strip()]
        if not keys:
            return {"status": "error", "summary": f"Invalid hotkey syntax: '{hotkey}'."}

        vks = []
        for k in keys:
            if k in VK_MAP:
                vks.append(VK_MAP[k])
            else:
                return {"status": "error", "summary": f"Unrecognized key '{k}' in hotkey combination."}

        user32 = ctypes.windll.user32

        # Press all modifier and target keys down in sequence
        for vk in vks:
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.02)

        time.sleep(0.04)

        # Release in reverse order
        for vk in reversed(vks):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)

        return {
            "status": "success",
            "summary": f"Executed hotkey '{hotkey.upper()}'.",
            "data": {"hotkey": hotkey, "keys": keys}
        }
    except Exception as e:
        return {"status": "error", "summary": f"Failed to press hotkey: {e}", "data": {"error": str(e)}}


@tool
def click_element_by_name(
    query: str,
    button: str = "left",
    double_click: bool = False,
    narration: str = ""
) -> Dict[str, Any]:
    """
    Autonomous Vision-to-Action loop:
    1. Uses local RapidOCR screen grounding to visually locate any target UI element, button, menu item, or icon.
    2. Smoothly glides the mouse cursor directly to the element's center.
    3. Clicks the element.
    
    Args:
        query: Name, text, or visual description of the target button or element on screen (e.g., 'File', 'Run', 'Terminal').
        button: 'left' or 'right' (default 'left').
        double_click: If True, double clicks the target element.
        narration: Optional voice or log narration of the action.
    """
    if not query or not query.strip():
        return {"status": "error", "summary": "Query cannot be empty."}

    query_clean = query.strip()
    try:
        # 1. Local OCR Grounding via OmniParser local tool
        from tools.omniparser_tool import locate_screen_element_local_only
        resolved = locate_screen_element_local_only(query=query_clean)

        if not resolved:
            return {
                "status": "error",
                "summary": f"Could not visually locate element matching '{query_clean}' on screen.",
                "data": {"query": query_clean}
            }

        target_x = resolved.get("center_x", resolved.get("x", 0))
        target_y = resolved.get("center_y", resolved.get("y", 0))

        # 2. Smoothly move cursor to element
        _ensure_input_desktop()
        _check_failsafe(target_x, target_y)
        _smooth_move(target_x, target_y, duration=0.35)
        time.sleep(0.06)

        # 3. Perform Click
        btn = button.lower().strip()
        click_type = "double" if double_click else "single"
        res_click = mouse_click.invoke({
            "x": target_x,
            "y": target_y,
            "button": btn,
            "click_type": click_type
        })

        summary_msg = f"Located '{query_clean}' (conf: {resolved.get('confidence', 1.0)*100:.0f}%) and executed {click_type} {btn}-click at ({target_x}, {target_y})."
        if narration:
            summary_msg = f"{narration} - {summary_msg}"

        return {
            "status": "success",
            "summary": summary_msg,
            "data": {
                "query": query_clean,
                "target_coordinates": {"x": target_x, "y": target_y},
                "bounding_box": {"x": resolved.get("x"), "y": resolved.get("y"), "w": resolved.get("w"), "h": resolved.get("h")},
                "confidence": resolved.get("confidence"),
                "click_result": res_click
            }
        }
    except CursorFailsafeException as e:
        return {"status": "aborted", "summary": str(e), "data": {"error": "failsafe"}}
    except Exception as e:
        return {"status": "error", "summary": f"Error in click_element_by_name for '{query_clean}': {e}", "data": {"error": str(e)}}


# ---------------------------------------------------------------------------
# System Metrics & Process Control (Maintained from OpenHuman adaptation)
# ---------------------------------------------------------------------------

@tool
def get_system_metrics() -> Dict[str, Any]:
    """
    Returns real-time system hardware statistics including CPU usage, RAM allocation, Disk space, and battery/uptime.
    """
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_cores = psutil.cpu_count(logical=True)

    mem = psutil.virtual_memory()
    mem_total_gb = round(mem.total / (1024**3), 2)
    mem_used_gb = round(mem.used / (1024**3), 2)
    mem_percent = mem.percent

    disk = psutil.disk_usage(os.getcwd())
    disk_free_gb = round(disk.free / (1024**3), 2)
    disk_total_gb = round(disk.total / (1024**3), 2)

    boot_time = psutil.boot_time()
    uptime_hours = round((time.time() - boot_time) / 3600, 1)

    return {
        "status": "success",
        "summary": f"System Telemetry: CPU: {cpu_percent}% ({cpu_cores} cores), RAM: {mem_used_gb}/{mem_total_gb} GB ({mem_percent}%), Disk: {disk_free_gb} GB free",
        "data": {
            "cpu_percent": cpu_percent,
            "cpu_cores": cpu_cores,
            "mem_total_gb": mem_total_gb,
            "mem_used_gb": mem_used_gb,
            "mem_percent": mem_percent,
            "disk_free_gb": disk_free_gb,
            "disk_total_gb": disk_total_gb,
            "uptime_hours": uptime_hours
        }
    }


@tool
def list_active_windows() -> Dict[str, Any]:
    """
    Enumerates running processes and open application windows on the desktop.
    """
    apps = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            name = info.get('name', '')
            if name and name.endswith('.exe') and info.get('memory_percent', 0) > 0.5:
                apps.append({
                    "pid": info.get('pid'),
                    "name": name,
                    "mem_percent": round(info.get('memory_percent', 0), 1)
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    apps_sorted = sorted(apps, key=lambda x: x['mem_percent'], reverse=True)[:15]

    return {
        "status": "success",
        "summary": f"Found {len(apps_sorted)} active high-resource desktop applications.",
        "data": {"applications": apps_sorted}
    }


@tool
def manage_clipboard(action: str = "read", text_to_write: str = "") -> Dict[str, Any]:
    """
    Reads from or writes text to the Windows system clipboard.
    
    Args:
        action: 'read' to get clipboard contents or 'write' to set clipboard contents.
        text_to_write: Text to copy to clipboard when action is 'write'.
    """
    if action == "read":
        try:
            cmd = "Get-Clipboard"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=3)
            clipboard_text = res.stdout.strip()
            return {
                "status": "success",
                "summary": f"Clipboard contents retrieved ({len(clipboard_text)} chars).",
                "data": {"content": clipboard_text}
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to read clipboard: {e}"}
    elif action == "write":
        try:
            p = subprocess.Popen(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $input"], stdin=subprocess.PIPE, text=True)
            p.communicate(input=text_to_write)
            return {
                "status": "success",
                "summary": f"Copied {len(text_to_write)} characters to clipboard.",
                "data": {"written_length": len(text_to_write)}
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to write clipboard: {e}"}
    else:
        return {"status": "error", "message": f"Invalid action '{action}'. Use 'read' or 'write'."}


# ---------------------------------------------------------------------------
# High-Level Autonomous Manipulation & Screen Navigation Tools
# ---------------------------------------------------------------------------
from tools.desktop_takeover_engine import desktop_operator

@tool
def smart_focus_window(window_title: str, maximize: bool = True) -> Dict[str, Any]:
    """
    Finds a desktop application or browser window by title and brings it to the foreground,
    bypassing Windows focus lockouts.
    
    Args:
        window_title: Search query for the window title (e.g., 'Canva', 'Chrome', 'Notepad', 'KiCad').
        maximize: If True, maximizes the window; otherwise restores normal size.
    """
    return desktop_operator.focus_window(window_title, maximize=maximize)


@tool
def smart_move_canvas_element(
    window_title: str,
    element_name: str,
    delta_x: int = -50,
    delta_y: int = 0,
    method: str = "drag"
) -> Dict[str, Any]:
    """
    Autonomously focuses a window, visually locates an element on the canvas (filtering out browser chrome/tabs),
    and repositions it by dragging or nudging, followed by verified displacement measurement.
    
    Args:
        window_title: Title or keyword of the application window (e.g., 'Canva', 'Presentation', 'Chrome').
        element_name: Name or visual text of the element to move (e.g., 'ROBOTIC', 'Header', 'Title').
        delta_x: Horizontal pixel displacement (negative moves left, positive moves right). Default -50px.
        delta_y: Vertical pixel displacement (negative moves up, positive moves down). Default 0px.
        method: 'drag' (mouse drag with hold physics) or 'nudge' (keyboard shift+arrow keys).
    """
    return desktop_operator.execute_smart_move(
        window_query=window_title,
        element_query=element_name,
        delta_x=delta_x,
        delta_y=delta_y,
        method=method
    )


@tool
def smart_click_canvas_element(
    window_title: str,
    element_name: str,
    button: str = "left",
    click_type: str = "single"
) -> Dict[str, Any]:
    """
    Focuses the specified window, visually locates an element on the canvas, and clicks it.
    
    Args:
        window_title: Title or keyword of the application window.
        element_name: Name or text of the element or button to click.
        button: 'left' or 'right' (default 'left').
        click_type: 'single' or 'double' (default 'single').
    """
    win_res = desktop_operator.focus_window(window_title)
    if win_res.get("status") == "error":
        return win_res
    time.sleep(0.4)
    elem = desktop_operator.locate_element_on_screen(element_name, exclude_browser_chrome=True)
    if not elem:
        return {"status": "error", "summary": f"Could not visually locate '{element_name}' in '{window_title}'."}

    desktop_operator.mouse_click(x=elem["center_x"], y=elem["center_y"], button=button, click_type=click_type)
    return {
        "status": "success",
        "summary": f"Clicked '{elem['text']}' at ({elem['center_x']}, {elem['center_y']}) in '{window_title}'.",
        "data": {"element": elem["text"], "coordinates": {"x": elem["center_x"], "y": elem["center_y"]}}
    }

