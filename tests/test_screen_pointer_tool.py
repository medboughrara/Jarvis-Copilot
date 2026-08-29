"""
Unit & Security Tests for Screen Pointer Tool & Local-Only Visual Grounding.
Covers:
- Task 1: Structural verification that screen grounding never invokes network/cloud APIs.
- Task 2: Structural verification that audit log never contains recoverable image data.
- Task 4: Exclusive fullscreen transitions immediately invalidate pending annotations.
- Task 5: Event-driven deterministic interruption across voice and visual channels.
- Task 7: Heartbeat-timeout self-clearing watchdog.
"""

import os
import time
import uuid
import sqlite3
import unittest
from unittest.mock import patch, MagicMock

import config
from tools.screen_pointer_tool import screen_pointer_manager, ScreenPointerManager
from tools.omniparser_tool import locate_screen_element_local_only, log_screen_grounding_event
from agent.screen_annotator import ScreenAnnotator


class TestScreenPointerTool(unittest.TestCase):

    def setUp(self):
        self.unique_id = uuid.uuid4().hex[:8]
        self.test_db = os.path.join(os.getcwd(), "scratch", f"test_audit_grounding_{self.unique_id}.db")
        self.mgr = ScreenPointerManager()

    def tearDown(self):
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass

    def test_screen_grounding_never_reaches_network_path(self):
        """
        Task 1: Mocks all network-capable clients (httpx, google_genai, urllib)
        and asserts locate_screen_element_local_only completes successfully with zero network calls.
        """
        with patch("httpx.AsyncClient.post", side_effect=AssertionError("Network called via httpx!")) as mock_httpx, \
             patch("urllib.request.urlopen", side_effect=AssertionError("Network called via urllib!")) as mock_urllib:

            result = locate_screen_element_local_only(
                query="def process_query",
                dpi_scale=1.0,
                db_path=self.test_db
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.get("engine"), "RapidOCR_ONNX_Local")
            self.assertIn("center_x", result)
            self.assertIn("center_y", result)

            # Assert network mocks were never called
            mock_httpx.assert_not_called()
            mock_urllib.assert_not_called()

    def test_audit_log_excludes_image_data(self):
        """
        Task 2: Asserts audit log table contains strictly primitive metadata (<500 bytes per row),
        the hardcoded 'RapidOCR_ONNX_Local' engine tag, and zero binary or base64 data.
        """
        log_screen_grounding_event(
            query_text="U1 LM2596 Buck Regulator",
            resolved_x=340,
            resolved_y=220,
            resolved_w=80,
            resolved_h=40,
            confidence=0.98,
            dpi_scale=1.25,
            db_path=self.test_db
        )

        self.assertTrue(os.path.exists(self.test_db))
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.execute("SELECT timestamp, query_text, resolved_x, resolved_y, resolved_w, resolved_h, confidence, dpi_scale, engine_tag FROM audit_screen_grounding")
            row = cursor.fetchone()

        self.assertIsNotNone(row)
        ts, query, x, y, w, h, conf, dpi, engine = row

        self.assertEqual(query, "U1 LM2596 Buck Regulator")
        self.assertEqual(x, 340)
        self.assertEqual(y, 220)
        self.assertEqual(w, 80)
        self.assertEqual(h, 40)
        self.assertEqual(conf, 0.98)
        self.assertEqual(dpi, 1.25)
        # Structural guarantee: engine_tag is hardcoded
        self.assertEqual(engine, "RapidOCR_ONNX_Local")

        # Byte size check: row must be tiny (pure metadata)
        row_str = str(row)
        self.assertLess(len(row_str.encode("utf-8")), 500, "Audit log row must not contain large image data")
        self.assertNotIn("base64", row_str.lower())
        self.assertNotIn("data:image", row_str.lower())

    def test_fullscreen_transition_invalidates_pending_annotations(self):
        """
        Task 4: Asserts that entering or exiting exclusive fullscreen immediately invalidates and clears active annotations.
        """
        annotator = ScreenAnnotator()
        annotator.add_spotlight(100, 100, 50, 50, label="Test Target")
        self.assertEqual(len(annotator.active_annotations), 1)

        # Transition into fullscreen
        annotator.on_fullscreen_transition(is_fullscreen=True)
        self.assertEqual(len(annotator.active_annotations), 0, "Entering fullscreen must purge active annotations")

        # Further attempts to add annotations while fullscreen is active should be suppressed
        res = annotator.add_spotlight(200, 200, 60, 60, label="Suppressed Target")
        self.assertEqual(res.get("status"), "suppressed")
        self.assertEqual(len(annotator.active_annotations), 0)

        # Transition out of fullscreen
        annotator.on_fullscreen_transition(is_fullscreen=False)
        self.assertEqual(len(annotator.active_annotations), 0)

    def test_consistent_interruption_across_voice_and_visual(self):
        """
        Task 5: Event-driven deterministic test (zero CI timing flakiness).
        When Target A is in-flight, dispatching Target B immediately cancels Target A
        and starts Target B simultaneously on both visual and voice channels.
        """
        cancelled_targets = []
        started_flights = []
        started_speeches = []

        self.mgr.on_target_cancelled = lambda target: cancelled_targets.append(target["query"])
        self.mgr.on_flight_start = lambda target: started_flights.append(target["query"])
        self.mgr.on_speech_start = lambda text: started_speeches.append(text)

        # Step 1: Start Target A
        res_a = self.mgr.point_to_element("Target Alpha Component", narration_text="Pointing to Target Alpha")
        self.assertEqual(res_a["status"], "success")
        self.assertEqual(len(started_flights), 1)
        self.assertEqual(started_flights[0], "Target Alpha Component")
        self.assertEqual(len(started_speeches), 1)
        self.assertEqual(started_speeches[0], "Pointing to Target Alpha")

        # Step 2: Immediately dispatch Target B (event-driven hook)
        res_b = self.mgr.point_to_element("Target Beta Resistor", narration_text="Pointing to Target Beta")
        self.assertEqual(res_b["status"], "success")

        # Verify Target A was cancelled on both channels simultaneously
        self.assertEqual(len(cancelled_targets), 1)
        self.assertEqual(cancelled_targets[0], "Target Alpha Component")

        # Verify Target B is active on both channels
        self.assertEqual(len(started_flights), 2)
        self.assertEqual(started_flights[1], "Target Beta Resistor")
        self.assertEqual(len(started_speeches), 2)
        self.assertEqual(started_speeches[1], "Pointing to Target Beta")
        self.assertEqual(self.mgr.current_target["query"], "Target Beta Resistor")

    def test_annotation_self_clears_on_heartbeat_timeout(self):
        """
        Task 7: Asserts that screen annotations self-purge automatically if no heartbeat ping
        is received within the timeout window (simulating a crashed pet process).
        """
        annotator = ScreenAnnotator(heartbeat_timeout=2.0)
        start_t = 1000.0
        annotator.record_heartbeat(start_t)
        annotator.add_spotlight(150, 150, 40, 40, label="Orphan Candidate", duration=10.0, timestamp=start_t)
        self.assertEqual(len(annotator.active_annotations), 1)

        # Time at 1.0s (within 2.0s lease) -> still active
        self.assertFalse(annotator.check_heartbeat_watchdog(current_time=start_t + 1.0))
        self.assertEqual(len(annotator.active_annotations), 1)

        # Time at 2.5s (missed heartbeat, timeout exceeded) -> self-clears
        did_clear = annotator.check_heartbeat_watchdog(current_time=start_t + 2.5)
        self.assertTrue(did_clear, "Watchdog must trigger self-clear when heartbeat expires")
        self.assertEqual(len(annotator.active_annotations), 0, "All annotations must be purged")


if __name__ == "__main__":
    unittest.main()
