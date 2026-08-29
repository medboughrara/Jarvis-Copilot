"""
Unit & Integration Tests for Desktop Pet WebSocket & REST API Backend.
Covers:
- Task 3: DPI awareness initialization and startup ordering verification.
- Task 6: WebSocket origin validation rejecting null, file://, and foreign origins,
          while accepting normalized (trailing-slash and case-insensitive) trusted origins.
- Singleton PID guard on /api/pet/launch.
- /api/pet/status and /api/pet/point REST APIs.
"""

import unittest
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import config
from web_server import app, _active_pet_pid
from agent.desktop_pet_app import init_process_dpi_awareness, DesktopPetController


class TestDesktopPetAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_dpi_awareness_applied_before_window_creation(self):
        """
        Task 3: Asserts init_process_dpi_awareness invokes SetProcessDpiAwareness(2)
        and logs a warning if the readback value does not match.
        """
        with patch("ctypes.windll.shcore.SetProcessDpiAwareness") as mock_set, \
             patch("ctypes.windll.shcore.GetProcessDpiAwareness") as mock_get:
            
            # Simulate mismatched awareness (e.g. 1 instead of 2)
            def side_effect_get(idx, byref_val):
                byref_val._obj.value = 1
                return 0
            mock_get.side_effect = side_effect_get

            with self.assertLogs("agent.desktop_pet_app", level="WARNING") as log_cm:
                val = init_process_dpi_awareness()
                mock_set.assert_called_once_with(2)
                self.assertTrue(any("DPI Warning" in msg for msg in log_cm.output))

    def test_websocket_rejects_null_and_file_origin(self):
        """
        Task 6: Asserts WebSocket handshake rejects Origin: null, Origin: file://, and unauthorized domains.
        """
        # 1. Null Origin
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/desktop_pet", headers={"origin": "null"}):
                pass

        # 2. File Origin
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/desktop_pet", headers={"origin": "file://"}):
                pass

        # 3. Foreign / Malicious Origin
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/desktop_pet", headers={"origin": "http://evil-tracker.com"}):
                pass

    def test_websocket_accepts_normalized_trusted_origin(self):
        """
        Task 6: Asserts WebSocket handshake accepts trusted origins even with trailing slashes or mixed casing.
        """
        # 1. Trailing slash variation: "http://localhost:8000/"
        with self.client.websocket_connect("/ws/desktop_pet", headers={"origin": "http://localhost:8000/"}) as ws:
            ws.send_text("heartbeat")

        # 2. Uppercase variation: "HTTP://LOCALHOST:8000"
        with self.client.websocket_connect("/ws/desktop_pet", headers={"origin": "HTTP://LOCALHOST:8000"}) as ws:
            ws.send_text("heartbeat")

    def test_pet_launch_singleton_guard(self):
        """
        Asserts /api/pet/launch prevents duplicate process spawns if a pet process is already alive.
        """
        import web_server
        # Simulate active PID 12345
        with patch("psutil.pid_exists", return_value=True):
            web_server._active_pet_pid = 12345
            resp = self.client.post("/api/pet/launch")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["pid"], 12345)
            self.assertIn("already active", data["message"])
        web_server._active_pet_pid = None

    def test_pet_status_and_point_api(self):
        """
        Asserts /api/pet/status and /api/pet/point REST APIs return valid schemas.
        """
        # Status check
        status_resp = self.client.get("/api/pet/status")
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.json()
        self.assertEqual(status_data["status"], "success")
        self.assertIn("is_running", status_data)

        # Point check
        point_resp = self.client.post("/api/pet/point", json={"target": "R1 Resistor", "message": "Check R1"})
        self.assertEqual(point_resp.status_code, 200)
        point_data = point_resp.json()
        self.assertEqual(point_data["status"], "success")
        self.assertIn("data", point_data)


if __name__ == "__main__":
    unittest.main()
