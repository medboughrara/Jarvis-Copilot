"""
Unit tests for tools/supply_chain_tool.py (Jarvis PCB Copilot).
"""

import unittest
from tools.supply_chain_tool import check_supply_chain_status

class TestSupplyChainTool(unittest.TestCase):
    def test_stm32f405_supply_chain(self):
        res = check_supply_chain_status.invoke({"part_number": "STM32F405RGT6"})
        self.assertEqual(res["status"], "success")
        self.assertIn("verdict", res["data"])
        self.assertEqual(res["data"]["verdict"], "PASSED")
        self.assertEqual(res["data"]["lifecycle"], "Active")

if __name__ == "__main__":
    unittest.main()
