"""
🧪 Unit Test Suite for MemPalace Memory Tool Integration.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath("."))

from tools.mempalace_tool import (
    remember_decision_or_fact,
    recall_verbatim_memory,
    get_mempalace_wake_up,
    mine_codebase_to_palace
)


class TestMemPalaceTool(unittest.TestCase):

    def test_remember_and_recall_verbatim_memory(self):
        # 1. Store a specific hardware design decision
        fact = "Microcontroller VDD decouple rule: 100nF 0402 ceramic capacitor placed <2mm from pin 18 with solid GND via."
        rem_res = remember_decision_or_fact.invoke({
            "content": fact,
            "room": "microcontroller_power",
            "hall": "rules",
            "wing": "test_wing"
        })
        self.assertIn(rem_res["status"], ["success", "error"])
        self.assertIn("Microcontroller", rem_res["data"]["content_preview"])

        # 2. Recall memory with semantic query
        query_res = recall_verbatim_memory.invoke({
            "query": "100nF decoupling capacitor pin 18",
            "wing": "test_wing"
        })
        self.assertEqual(query_res["status"], "success")
        self.assertIn("query", query_res["data"])

    def test_get_mempalace_wake_up(self):
        wake_res = get_mempalace_wake_up.invoke({"wing": "jarvis_pcb"})
        self.assertEqual(wake_res["status"], "success")
        self.assertIn("wake_up_text", wake_res["data"])


if __name__ == "__main__":
    unittest.main()
