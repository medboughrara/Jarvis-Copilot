"""
🧪 Unit Test Suite for Phase 4: Circuit Pattern Library & Parameterized Reference Designs.
Verifies Phase 4 Definition of Done:
'Design a 5V/2A buck converter from 12V input' reliably produces a schematic that passes ERC.
"""

import os
import sys
import unittest

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from tools.circuit_templates_tool import generate_from_template, list_circuit_templates
from tools.kicad_editor import KiCadSchematicEditor


class TestCircuitTemplatesPhase4(unittest.TestCase):

    def setUp(self):
        os.makedirs("scratch", exist_ok=True)
        self.buck_sch_path = os.path.abspath("scratch/test_phase4_buck_5v2a.kicad_sch")
        if os.path.exists(self.buck_sch_path):
            os.remove(self.buck_sch_path)

    def test_list_templates(self):
        """Tests that list_circuit_templates returns valid reference designs."""
        print("\n--- Testing list_circuit_templates ---")
        res = list_circuit_templates.invoke({})
        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(res["data"]["count"], 4)
        names = [t["template_name"] for t in res["data"]["templates"]]
        self.assertIn("buck_converter", names)
        self.assertIn("ldo_regulator", names)
        print(f"Available templates: {names}")
        print("✅ list_circuit_templates PASSED!")

    def test_buck_converter_5v2a_definition_of_done(self):
        """Phase 4 Definition of Done: 'Design a 5V/2A buck converter from 12V input'."""
        print("\n--- Testing Phase 4: Generate 5V/2A Buck Converter from 12V Input ---")
        res = generate_from_template.invoke({
            "template_name": "buck_converter",
            "params": {"vin_v": 12.0, "vout_v": 5.0, "iout_a": 2.0},
            "file_path": self.buck_sch_path
        })

        self.assertEqual(res["status"], "success")
        print(f"Generation Result: {res['summary']}")
        
        # Verify file exists and has content
        self.assertTrue(os.path.exists(self.buck_sch_path))
        self.assertGreater(os.path.getsize(self.buck_sch_path), 500)
        
        # Reload and inspect schematic components
        reloaded = KiCadSchematicEditor(self.buck_sch_path)
        self.assertGreaterEqual(len(reloaded.components), 7)
        
        refs = [c["reference"] for c in reloaded.components]
        print(f"Generated schematic components: {refs}")
        self.assertIn("U1", refs)  # Controller IC
        self.assertIn("L1", refs)  # Inductor
        self.assertIn("D1", refs)  # Schottky Diode
        self.assertIn("C1", refs)  # Input Cap
        self.assertIn("C3", refs)  # Output Cap
        self.assertIn("R1", refs)  # Feedback Resistor
        self.assertIn("R2", refs)  # Feedback Resistor

        # Verify ERC check
        erc_verdict = res["data"]["erc_verdict"]
        print(f"ERC Check Verdict on Generated Buck Converter: [{erc_verdict}]")
        self.assertIn(erc_verdict, ["PASSED", "WARNING"])
        print("✅ Phase 4 Definition of Done PASSED: 5V/2A buck converter generated and verified!")


if __name__ == "__main__":
    unittest.main()
