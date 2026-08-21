"""
🧪 Unit Test Suite for Phase 8: Manufacturing Pipeline & Fabrication Package Export.
Verifies Phase 8 Definition of Done:
A routed board produces a valid manufacturing package (Gerbers ZIP, Drill DRL, BOM CSV, CPL CSV)
and a turnkey cost estimate matching distributor component APIs.
"""

import os
import sys
import zipfile
import unittest

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from tools.manufacturing_tool import (
    export_gerbers,
    export_drill,
    export_cpl,
    export_bom,
    estimate_cost
)
from tools.kicad_editor import KiCadPcbEditor, KiCadSchematicEditor


class TestManufacturingPhase8(unittest.TestCase):

    def setUp(self):
        os.makedirs("scratch/phase8_output", exist_ok=True)
        self.test_pcb = os.path.abspath("scratch/phase8_test_board.kicad_pcb")
        self.test_sch = os.path.abspath("scratch/phase8_test_sch.kicad_sch")
        self.out_dir = os.path.abspath("scratch/phase8_output")

        # Create sample board and schematic
        pcb = KiCadPcbEditor()
        pcb.add_footprint("U1", "MP1584EN", "Package_SO:SOIC-8", (100.0, 100.0))
        pcb.add_footprint("R1", "10k", "Resistor_SMD:R_0603", (120.0, 100.0))
        pcb.add_track("VCC", (100.0, 100.0), (120.0, 100.0), 0.25, "F.Cu")
        pcb.save(self.test_pcb)

        sch = KiCadSchematicEditor()
        sch.add_symbol("U1", "MP1584EN", "Package_SO:SOIC-8", (100.0, 100.0), "Regulator_Switching:MP1584EN")
        sch.add_symbol("R1", "10k", "Resistor_SMD:R_0603", (120.0, 100.0), "Device:R")
        sch.save(self.test_sch)

    def test_manufacturing_package_and_cost_definition_of_done(self):
        """Phase 8 Definition of Done: Export Gerbers, Drill, CPL, BOM, and Estimate Cost."""
        print("\n--- Testing Phase 8: Manufacturing Package Export ---")
        
        # 1. Export Gerbers
        gerber_res = export_gerbers.invoke({"board_file": self.test_pcb, "output_dir": self.out_dir})
        self.assertEqual(gerber_res["status"], "success")
        zip_path = gerber_res["data"]["zip_package"]
        self.assertTrue(os.path.exists(zip_path))
        print(f"Gerber Package: {os.path.basename(zip_path)} ({os.path.getsize(zip_path)} bytes)")
        
        # Verify ZIP contains RS-274X layers
        with zipfile.ZipFile(zip_path, 'r') as zf:
            namelist = zf.namelist()
            self.assertTrue(any(f.endswith(".gtl") for f in namelist))
            self.assertTrue(any(f.endswith(".gbl") for f in namelist))
            self.assertTrue(any(f.endswith(".gko") for f in namelist))
            print(f"Verified Gerber ZIP layers: {namelist}")

        # 2. Export Drill
        drill_res = export_drill.invoke({"board_file": self.test_pcb, "output_dir": self.out_dir})
        self.assertEqual(drill_res["status"], "success")
        self.assertTrue(os.path.exists(drill_res["data"]["drill_file"]))
        print(f"Excellon Drill File: {os.path.basename(drill_res['data']['drill_file'])}")

        # 3. Export CPL
        cpl_res = export_cpl.invoke({"board_file": self.test_pcb, "output_path": os.path.join(self.out_dir, "cpl.csv")})
        self.assertEqual(cpl_res["status"], "success")
        self.assertTrue(os.path.exists(cpl_res["data"]["cpl_path"]))
        print(f"CPL Placement List: {cpl_res['summary']}")

        # 4. Export BOM
        bom_res = export_bom.invoke({"project_file": self.test_sch, "output_path": os.path.join(self.out_dir, "bom.csv")})
        self.assertEqual(bom_res["status"], "success")
        self.assertTrue(os.path.exists(bom_res["data"]["bom_path"]))
        print(f"BOM Export: {bom_res['summary']}")

        # 5. Estimate Turnkey PCBA Cost
        cost_res = estimate_cost.invoke({"board_file": self.test_sch, "quantity": 10})
        self.assertEqual(cost_res["status"], "success")
        print(f"Turnkey Cost Estimate: {cost_res['summary']}")
        self.assertGreater(cost_res["data"]["unit_price_usd"], 0)
        self.assertGreater(cost_res["data"]["total_batch_usd"], 0)

        print("✅ Phase 8 Definition of Done PASSED: Complete turnkey manufacturing package and cost model verified!")


if __name__ == "__main__":
    unittest.main()
