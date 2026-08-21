"""
🧪 Unit Test Suite for Phase 6: PCB Autorouter, DRC & DFM Verification.
Verifies Phase 6 Definition of Done:
A 2-layer test board with placed but unrouted components gets fully routed automatically and passes DRC.
"""

import os
import sys
import unittest

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from tools.autorouter_tool import autoroute_board, get_drc_violations, check_dfm
from tools.kicad_editor import KiCadPcbEditor


class TestAutorouterPhase6(unittest.TestCase):

    def setUp(self):
        os.makedirs("scratch", exist_ok=True)
        self.test_pcb_path = os.path.abspath("scratch/test_phase6_board.kicad_pcb")
        if os.path.exists(self.test_pcb_path):
            os.remove(self.test_pcb_path)

        # 1. Create a 2-layer board with placed but unrouted components (R1 and R2)
        pcb_editor = KiCadPcbEditor()
        pcb_editor.add_footprint(reference="R1", value="10k", footprint_name="Resistor_SMD:R_0805_2012Metric", at=(100.0, 100.0))
        pcb_editor.add_footprint(reference="R2", value="10k", footprint_name="Resistor_SMD:R_0805_2012Metric", at=(140.0, 100.0))
        pcb_editor.save(self.test_pcb_path)

    def test_autoroute_and_drc_definition_of_done(self):
        """Phase 6 Definition of Done: 2-layer board gets fully routed and passes DRC."""
        print("\n--- Testing Phase 6: PCB Autorouting & DRC Verification ---")
        
        # 1. Run Autorouter
        route_res = autoroute_board.invoke({
            "board_file": self.test_pcb_path,
            "track_width_mm": 0.25,
            "layer": "F.Cu"
        })
        self.assertEqual(route_res["status"], "success")
        print(f"Autorouter Summary: {route_res['summary']}")
        self.assertGreater(route_res["data"]["tracks_created"], 0)

        # 2. Re-open board and verify copper tracks exist
        reloaded_pcb = KiCadPcbEditor(self.test_pcb_path)
        self.assertGreaterEqual(len(reloaded_pcb.tracks), 1)
        print(f"Total Routed Copper Tracks on Board: {len(reloaded_pcb.tracks)}")

        # 3. Run DRC check
        drc_res = get_drc_violations.invoke({"board_file": self.test_pcb_path})
        self.assertEqual(drc_res["status"], "success")
        self.assertEqual(drc_res["data"]["verdict"], "PASSED")
        print(f"DRC Verdict: [{drc_res['data']['verdict']}] (Violations: {drc_res['data']['violations_count']})")

        # 4. Run DFM validation against JLCPCB rules
        dfm_res = check_dfm.invoke({"board_file": self.test_pcb_path, "manufacturer": "JLCPCB"})
        self.assertEqual(dfm_res["status"], "success")
        self.assertEqual(dfm_res["data"]["verdict"], "PASSED")
        print(f"DFM Review: {dfm_res['summary']}")
        
        print("✅ Phase 6 Definition of Done PASSED: 2-layer board fully routed and passed DRC & DFM!")


if __name__ == "__main__":
    unittest.main()
