"""
Unit tests for agent/session_context.py (JarvisSessionContext per-session isolation).
"""

import unittest
from agent.session_context import JarvisSessionContext


class TestSessionContext(unittest.TestCase):
    def test_session_cache_isolation(self):
        session1 = JarvisSessionContext("session_1")
        session2 = JarvisSessionContext("session_2")

        session1.cache_schematic_model("hash_123", {"model_name": "model_1"})
        session2.cache_schematic_model("hash_456", {"model_name": "model_2"})

        self.assertEqual(session1.get_schematic_model("hash_123"), {"model_name": "model_1"})
        self.assertIsNone(session1.get_schematic_model("hash_456"))

        self.assertEqual(session2.get_schematic_model("hash_456"), {"model_name": "model_2"})
        self.assertIsNone(session2.get_schematic_model("hash_123"))

    def test_lazy_engine_instantiation(self):
        session = JarvisSessionContext("session_test")
        self.assertIsNotNone(session.get_rag_engine())
        self.assertIsNotNone(session.get_omniparser_engine())
        self.assertIsNotNone(session.get_unlimited_ocr_engine())


if __name__ == "__main__":
    unittest.main()
