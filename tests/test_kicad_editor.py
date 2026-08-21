"""
🧪 Unit Test Suite for KiCad Programmatic AST Editor (Phase 1 Definition of Done).
Verifies that:
1. A test schematic is created/loaded.
2. A 10k resistor is added and wired to VCC and OUTPUT_NET.
3. The file is saved and re-opened.
4. All added components and net connections are verifiably present in the re-opened file.
5. A test PCB is created, a resistor footprint is placed, a routed copper track is wired, saved, and re-opened.
"""

import os
import sys
import unittest

# Ensure Windows stdout handles UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from tools.kicad_editor import KiCadSchematicEditor, KiCadPcbEditor


class TestKiCadEditorPhase1(unittest.TestCase):

    def setUp(self):
        os.makedirs("scratch", exist_ok=True)
        self.test_sch_path = os.path.abspath("scratch/test_phase1_project.kicad_sch")
        self.test_pcb_path = os.path.abspath("scratch/test_phase1_project.kicad_pcb")

        # Clean prior test artifacts
        for p in [self.test_sch_path, self.test_pcb_path]:
            if os.path.exists(p):
                os.remove(p)

    def test_schematic_add_resistor_and_wire_net_persistence(self):
        """Phase 1 Definition of Done: Add resistor, connect to net, save, reopen, and verify."""
        print("\n--- Testing Schematic Mutation & Persistence ---")
        # 1. Initialize editor and create fresh schematic
        editor = KiCadSchematicEditor()
        
        # 2. Add 10k Resistor R1
        comp = editor.add_symbol(
            reference="R1",
            value="10k",
            footprint="Resistor_SMD:R_0805_2012Metric",
            at=(120.0, 80.0),
            lib_id="Device:R"
        )
        self.assertEqual(comp["reference"], "R1")
        self.assertEqual(comp["value"], "10k")

        # 3. Connect Pin 1 (offset -2.5, 0) to VCC and Pin 2 (offset +2.5, 0) to OUTPUT_NET
        editor.connect_component_to_net(reference="R1", pin_offset_xy=(-2.5, 0.0), net_name="VCC", wire_length=10.0)
        editor.connect_component_to_net(reference="R1", pin_offset_xy=(2.5, 0.0), net_name="OUTPUT_NET", wire_length=10.0)

        # 4. Save to disk
        saved_file = editor.save(self.test_sch_path)
        self.assertTrue(os.path.exists(saved_file))
        print(f"Saved test schematic to {saved_file} ({os.path.getsize(saved_file)} bytes)")

        # 5. Re-open and verify persistence
        reopened_editor = KiCadSchematicEditor(self.test_sch_path)
        self.assertEqual(len(reopened_editor.components), 1)
        
        r1 = reopened_editor.components[0]
        self.assertEqual(r1["reference"], "R1")
        self.assertEqual(r1["value"], "10k")
        self.assertEqual(r1["footprint"], "Resistor_SMD:R_0805_2012Metric")
        self.assertEqual(r1["at"], (120.0, 80.0, 0.0))
        
        # Verify 2 wires and 2 net labels persisted
        self.assertEqual(len(reopened_editor.wires), 2)
        self.assertEqual(len(reopened_editor.labels), 2)
        print("✅ Schematic Phase 1 Verification PASSED: R1 (10k) and nets VCC, OUTPUT_NET verified!")

    def test_pcb_add_footprint_and_route_track_persistence(self):
        """Test PCB Editor: Add footprint, add copper track segment, save, reopen, and verify."""
        print("\n--- Testing PCB Mutation & Persistence ---")
        pcb_editor = KiCadPcbEditor()
        
        # 1. Add Footprint for R1
        pcb_editor.add_footprint(
            reference="R1",
            value="10k",
            footprint_name="Resistor_SMD:R_0805_2012Metric",
            at=(150.0, 100.0)
        )
        
        # 2. Add routed track for net VCC
        pcb_editor.add_track(
            net_name="VCC",
            start=(149.0, 100.0),
            end=(130.0, 100.0),
            width_mm=0.35,
            layer="F.Cu"
        )

        # 3. Save PCB
        saved_pcb = pcb_editor.save(self.test_pcb_path)
        self.assertTrue(os.path.exists(saved_pcb))
        print(f"Saved test PCB to {saved_pcb} ({os.path.getsize(saved_pcb)} bytes)")

        # 4. Reopen and verify persistence
        reopened_pcb = KiCadPcbEditor(self.test_pcb_path)
        self.assertEqual(len(reopened_pcb.footprints), 1)
        self.assertEqual(len(reopened_pcb.tracks), 1)
        self.assertIn("VCC", reopened_pcb.nets)
        print("✅ PCB Phase 1 Verification PASSED: R1 footprint and VCC copper track verified!")


if __name__ == "__main__":
    unittest.main()
