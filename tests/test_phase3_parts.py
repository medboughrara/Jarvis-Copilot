"""
🧪 Unit Test Suite for Phase 3: Component + Datasheet Layer.
Verifies Phase 3 Definition of Done:
search_parts("low power MCU for battery operation") returns relevant, real components from the indexed library.
"""

import os
import sys
import unittest

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from tools.parts_search_tool import search_parts, parse_component_datasheet


class TestPartsSearchPhase3(unittest.TestCase):

    def test_search_parts_low_power_mcu_definition_of_done(self):
        """Phase 3 Definition of Done: search_parts('low power MCU for battery operation')."""
        print("\n--- Testing Phase 3: search_parts for Low Power MCU ---")
        res = search_parts.invoke({"query": "low power MCU for battery operation"})
        
        self.assertEqual(res["status"], "success")
        self.assertGreater(len(res["data"]["parts"]), 0)
        
        # Verify top results contain relevant low power MCUs (STM32L4, nRF52840, or ATtiny85)
        mpns = [p["mpn"] for p in res["data"]["parts"]]
        print(f"Matched MPNs for query: {mpns}")
        print(f"Top Match Summary: {res['summary']}")
        
        has_low_power_mcu = any(m in ["STM32L431CBT6", "nRF52840-QIAA", "ATtiny85-20SU"] for m in mpns)
        self.assertTrue(has_low_power_mcu, f"Expected low power MCU in results, got: {mpns}")
        
        top_part = res["data"]["parts"][0]
        self.assertIn("voltage_range", top_part)
        self.assertIn("footprint", top_part)
        self.assertIn("lib_id", top_part)
        print(f"Top Part: {top_part['mpn']} | Footprint: {top_part['footprint']} | V: {top_part['voltage_range']}")
        print("✅ Phase 3 Definition of Done PASSED: Low power MCU returned from indexed library!")

    def test_search_parts_voltage_regulators(self):
        """Test parametric search for 3.3V LDO regulator."""
        print("\n--- Testing search_parts for 3.3V LDO ---")
        res = search_parts.invoke({"query": "3.3V LDO regulator"})
        self.assertEqual(res["status"], "success")
        mpns = [p["mpn"] for p in res["data"]["parts"]]
        self.assertIn("AP2112K-3.3TRG1", mpns)
        print(f"Found LDO: {mpns}")
        print("✅ LDO Parametric Search PASSED!")


if __name__ == "__main__":
    unittest.main()
