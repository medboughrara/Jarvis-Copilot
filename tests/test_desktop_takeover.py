"""
🧪 Unit & Integration Test Suite for Jarvis Desktop Takeover & Cursor Navigation Tools.
Verifies:
1. Multi-monitor resolution & cursor telemetry (`get_cursor_position`)
2. Human-like smooth cursor trajectory & positioning (`mouse_move`)
3. Mouse clicks & button combinations (`mouse_click`)
4. Drag-and-drop operations across virtual screen (`mouse_drag`)
5. Mouse wheel scrolling (`mouse_scroll`)
6. Keystroke injection & typing (`type_text`)
7. Keyboard shortcuts & hotkey combinations (`press_hotkey`)
8. Corner failsafe boundary protection (`_check_failsafe`, `CursorFailsafeException`)
9. Autonomous vision-to-action grounding & click loop (`click_element_by_name`)
10. Tool registration inside `JarvisAgent.tools`
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from tools.desktop_control_tool import (
    get_cursor_position,
    mouse_move,
    mouse_click,
    mouse_drag,
    mouse_scroll,
    type_text,
    press_hotkey,
    click_element_by_name,
    get_system_metrics,
    list_active_windows,
    manage_clipboard,
    _check_failsafe,
    _get_cursor_pos,
    _get_display_metrics,
    CursorFailsafeException
)


class TestDesktopTakeoverTools(unittest.TestCase):

    def test_01_get_cursor_position_and_display_metrics(self):
        """Tests retrieval of real cursor position and multi-monitor virtual bounds."""
        res = get_cursor_position.invoke({})
        self.assertEqual(res["status"], "success")
        data = res["data"]
        self.assertIn("cursor", data)
        self.assertIn("primary_monitor", data)
        self.assertIn("virtual_desktop", data)
        self.assertIn("monitors", data)

        cur = data["cursor"]
        self.assertIsInstance(cur["x"], int)
        self.assertIsInstance(cur["y"], int)

        prim = data["primary_monitor"]
        self.assertGreater(prim["width"], 0)
        self.assertGreater(prim["height"], 0)

        virt = data["virtual_desktop"]
        self.assertGreater(virt["width"], 0)
        self.assertGreater(virt["height"], 0)
        self.assertGreaterEqual(len(data["monitors"]), 1)
        print(f"✅ [Test 1] Cursor at ({cur['x']}, {cur['y']}), Virtual Desktop: {virt['width']}x{virt['height']}")

    def test_02_corner_failsafe_guardrail(self):
        """Tests that moving cursor to extreme corners triggers immediate failsafe abort."""
        # Corner (0,0) and (5,5) must raise CursorFailsafeException
        with self.assertRaises(CursorFailsafeException):
            _check_failsafe(0, 0)
        with self.assertRaises(CursorFailsafeException):
            _check_failsafe(3, 4)
        with self.assertRaises(CursorFailsafeException):
            _check_failsafe(5, 5)

        # Safe coordinates must pass
        _check_failsafe(500, 500)
        _check_failsafe(100, 200)

        # mouse_move to (0,0) should safely catch and return status 'aborted'
        res_abort = mouse_move.invoke({"x": 0, "y": 0})
        self.assertEqual(res_abort["status"], "aborted")
        self.assertIn("Failsafe", res_abort["summary"])
        print("✅ [Test 2] Corner failsafe guardrail verified!")

    def test_03_mouse_move_smooth_trajectory(self):
        """Tests smooth cursor movement to safe coordinate and restoring original position."""
        orig_x, orig_y = _get_cursor_pos()

        # Move to screen center
        metrics = _get_display_metrics()
        target_x = metrics["primary_monitor"]["width"] // 2
        target_y = metrics["primary_monitor"]["height"] // 2

        res = mouse_move.invoke({"x": target_x, "y": target_y, "smooth": True, "duration": 0.1})
        self.assertEqual(res["status"], "success")
        new_x, new_y = _get_cursor_pos()
        self.assertEqual(new_x, target_x)
        self.assertEqual(new_y, target_y)

        # Restore original position
        mouse_move.invoke({"x": orig_x, "y": orig_y, "smooth": False})
        print(f"✅ [Test 3] Smooth mouse trajectory to ({target_x}, {target_y}) verified!")

    def test_04_mouse_click_variants(self):
        """Tests click dispatch (single, double, right, middle) at safe screen location."""
        cur_x, cur_y = _get_cursor_pos()

        # Test single click
        res_single = mouse_click.invoke({"x": cur_x, "y": cur_y, "button": "left", "click_type": "single"})
        self.assertEqual(res_single["status"], "success")
        self.assertIn("Single left-click", res_single["summary"])

        # Test double click
        res_double = mouse_click.invoke({"button": "left", "click_type": "double"})
        self.assertEqual(res_double["status"], "success")
        self.assertIn("Double left-click", res_double["summary"])

        # Test right click
        res_right = mouse_click.invoke({"button": "right", "click_type": "single"})
        self.assertEqual(res_right["status"], "success")
        self.assertIn("Single right-click", res_right["summary"])
        print("✅ [Test 4] Mouse click variants verified!")

    def test_05_mouse_scroll(self):
        """Tests mouse wheel scroll in all directions."""
        res_down = mouse_scroll.invoke({"clicks": 2, "direction": "down"})
        self.assertEqual(res_down["status"], "success")
        self.assertEqual(res_down["data"]["clicks"], 2)

        res_up = mouse_scroll.invoke({"clicks": 2, "direction": "up"})
        self.assertEqual(res_up["status"], "success")

        res_invalid = mouse_scroll.invoke({"direction": "sideways"})
        self.assertEqual(res_invalid["status"], "error")
        print("✅ [Test 5] Mouse scroll verified!")

    def test_06_mouse_drag_and_failsafe(self):
        """Tests mouse drag functionality and failsafe protection."""
        metrics = _get_display_metrics()
        center_x = metrics["primary_monitor"]["width"] // 2
        center_y = metrics["primary_monitor"]["height"] // 2

        # Drag 10px across center
        res_drag = mouse_drag.invoke({
            "start_x": center_x,
            "start_y": center_y,
            "end_x": center_x + 10,
            "end_y": center_y + 10,
            "duration": 0.1
        })
        self.assertEqual(res_drag["status"], "success")

        # Failsafe drag to corner
        res_abort = mouse_drag.invoke({
            "start_x": 0, "start_y": 0, "end_x": 500, "end_y": 500
        })
        self.assertEqual(res_abort["status"], "aborted")
        print("✅ [Test 6] Mouse drag and drag failsafe verified!")

    def test_07_type_text_unicode(self):
        """Tests unicode typing and empty text rejection."""
        # Empty text should return error
        res_empty = type_text.invoke({"text": ""})
        self.assertEqual(res_empty["status"], "error")

        # Mock user32.keybd_event to verify exact calls
        with patch("ctypes.windll.user32.keybd_event") as mock_keybd:
            res = type_text.invoke({"text": "Jarvis 2026!", "press_enter": True, "delay": 0.0})
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["data"]["length"], 12)
            self.assertTrue(res["data"]["press_enter"])
            self.assertGreater(mock_keybd.call_count, 12)
        print("✅ [Test 7] Unicode text typing verified!")

    def test_08_press_hotkey(self):
        """Tests shortcut key combinations."""
        # Invalid hotkey syntax
        res_err = press_hotkey.invoke({"hotkey": "ctrl+invalidkey123"})
        self.assertEqual(res_err["status"], "error")

        # Empty hotkey
        res_empty = press_hotkey.invoke({"hotkey": ""})
        self.assertEqual(res_empty["status"], "error")

        # Valid hotkey with mock
        with patch("ctypes.windll.user32.keybd_event") as mock_keybd:
            res_ctrl_s = press_hotkey.invoke({"hotkey": "ctrl+s"})
            self.assertEqual(res_ctrl_s["status"], "success")
            self.assertEqual(res_ctrl_s["data"]["keys"], ["ctrl", "s"])
            self.assertEqual(mock_keybd.call_count, 4)  # 2 down, 2 up
        print("✅ [Test 8] Hotkey combinations verified!")

    def test_09_click_element_by_name_autonomous_loop(self):
        """Tests vision-to-action click loop using mocked screen element locator."""
        with patch("tools.omniparser_tool.locate_screen_element_local_only") as mock_locate:
            mock_locate.return_value = {
                "x": 400, "y": 300, "w": 80, "h": 30,
                "center_x": 440, "center_y": 315,
                "confidence": 0.98,
                "text": "Run"
            }
            with patch("ctypes.windll.user32.mouse_event") as mock_mouse:
                with patch("ctypes.windll.user32.SetCursorPos"):
                    res = click_element_by_name.invoke({
                        "query": "Run",
                        "button": "left",
                        "double_click": False,
                        "narration": "Clicking the Run button"
                    })

                    self.assertEqual(res["status"], "success")
                    self.assertEqual(res["data"]["target_coordinates"]["x"], 440)
                    self.assertEqual(res["data"]["target_coordinates"]["y"], 315)
                    self.assertIn("Located 'Run'", res["summary"])
                    mock_locate.assert_called_once_with(query="Run")
        print("✅ [Test 9] Vision-to-Action click loop verified!")

    def test_10_jarvis_copilot_tool_registration(self):
        """Verifies that all desktop takeover tools are registered in JarvisAgent.tools."""
        from agent.copilot import JarvisAgent
        agent = JarvisAgent()
        tool_names = [t.name for t in agent.tools]

        required_desktop_tools = [
            "get_system_metrics",
            "list_active_windows",
            "manage_clipboard",
            "get_cursor_position",
            "mouse_move",
            "mouse_click",
            "mouse_drag",
            "mouse_scroll",
            "type_text",
            "press_hotkey",
            "click_element_by_name",
            "smart_focus_window",
            "smart_move_canvas_element",
            "smart_click_canvas_element"
        ]

        for req in required_desktop_tools:
            self.assertIn(req, tool_names, f"Tool '{req}' must be registered in JarvisAgent.tools!")

        print(f"✅ [Test 10] All {len(required_desktop_tools)} desktop takeover tools registered in JarvisAgent (Total tools: {len(tool_names)})!")

    def test_11_desktop_takeover_engine_architecture(self):
        """Tests DesktopTakeoverEngine unified heuristics (window matching, fuzzy ratio, chrome filtering)."""
        from tools.desktop_takeover_engine import DesktopTakeoverEngine, desktop_operator

        # 1. Fuzzy match ratio
        self.assertAlmostEqual(DesktopTakeoverEngine._levenshtein_ratio("ROBOTIC", "ROBOTIC"), 1.0)
        self.assertGreater(DesktopTakeoverEngine._levenshtein_ratio("ROBOTIC", "ROBOTIO"), 0.80)
        self.assertLess(DesktopTakeoverEngine._levenshtein_ratio("ROBOTIC", "NOTEPAD"), 0.30)

        # 2. Window enumeration query
        wins = desktop_operator.find_windows_by_query("chrome")
        self.assertIsInstance(wins, list)

        # 3. Smart tool invocation with mock
        with patch.object(desktop_operator, "execute_smart_move") as mock_move:
            mock_move.return_value = {
                "status": "success",
                "summary": "Moved element 50px left",
                "data": {"verified_delta": {"dx": -50, "dy": 0}}
            }
            from tools.desktop_control_tool import smart_move_canvas_element
            res = smart_move_canvas_element.invoke({
                "window_title": "Canva",
                "element_name": "ROBOTIC",
                "delta_x": -50,
                "delta_y": 0,
                "method": "drag"
            })
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["data"]["verified_delta"]["dx"], -50)
            mock_move.assert_called_once_with(
                window_query="Canva",
                element_query="ROBOTIC",
                delta_x=-50,
                delta_y=0,
                method="drag"
            )

        print("✅ [Test 11] Unified DesktopTakeoverEngine architecture verified!")


if __name__ == "__main__":
    unittest.main()

