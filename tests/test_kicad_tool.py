"""
Unit and Integration Tests for tools/kicad_tool.py (AutoPick Jarvis Copilot).
"""

import os
import unittest
from tools.kicad_tool import KiCadParser, analyze_kicad_file, get_power_tree, check_pcb_errors


SAMPLE_KICAD_SCH = """(kicad_sch (version 20230121) (generator eeschema)
  (paper "A4")
  (symbol (lib_id "MCU_ST_STM32F4:STM32F405RGT6") (at 100 100 0) (unit 1)
    (property "Reference" "U1" (id 0) (at 100 90 0))
    (property "Value" "STM32F405RGT6" (id 1) (at 100 110 0))
  )
  (symbol (lib_id "Driver_Motor:PCA9685PW") (at 150 100 0) (unit 1)
    (property "Reference" "U2" (id 0) (at 150 90 0))
    (property "Value" "PCA9685_ServoDriver" (id 1) (at 150 110 0))
  )
  (symbol (lib_id "Regulator_Linear:AMS1117-3.3") (at 200 100 0) (unit 1)
    (property "Reference" "U3" (id 0) (at 200 90 0))
    (property "Value" "AMS1117-3.3" (id 1) (at 200 110 0))
  )
  (symbol (lib_id "Connector:Servo_Header") (at 250 100 0) (unit 1)
    (property "Reference" "J1" (id 0) (at 250 90 0))
    (property "Value" "Servomotor_Arm_Joint1" (id 1) (at 250 110 0))
  )
  (symbol (lib_id "Device:C") (at 110 120 0) (unit 1)
    (property "Reference" "C1" (id 0) (at 110 120 0))
    (property "Value" "100nF" (id 1) (at 110 130 0))
  )
  (symbol (lib_id "Device:C") (at 120 120 0) (unit 1)
    (property "Reference" "C2" (id 0) (at 120 120 0))
    (property "Value" "10uF" (id 1) (at 120 130 0))
  )
  (wire (pts (xy 100 100) (xy 150 100)) (node "GND") (node "+3V3") (node "+12V") (node "VMOTOR"))
)
"""


class TestKiCadTool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_file = os.path.join(os.getcwd(), "tests", "sample_autopick.kicad_sch")
        os.makedirs(os.path.dirname(cls.test_file), exist_ok=True)
        with open(cls.test_file, "w", encoding="utf-8") as f:
            f.write(SAMPLE_KICAD_SCH)

    def test_extract_components(self):
        parser = KiCadParser(self.test_file)
        comps = parser.extract_components()
        self.assertGreaterEqual(len(comps), 4)
        refs = [c["reference"] for c in comps]
        self.assertIn("U1", refs)
        self.assertIn("U2", refs)
        self.assertIn("J1", refs)

    def test_power_tree_generation(self):
        parser = KiCadParser(self.test_file)
        tree = parser.generate_power_tree()
        self.assertIn("AutoPick PCB Power Tree Analysis", tree)
        self.assertIn("STM32F405RGT6", tree)

    def test_erc_checks(self):
        parser = KiCadParser(self.test_file)
        erc_result = parser.run_erc_checks()
        self.assertTrue(isinstance(erc_result, str))

    def test_bom_generation(self):
        parser = KiCadParser(self.test_file)
        result = parser.generate_bom()
        self.assertIn("BOM generated for", result)
        self.assertTrue(os.path.exists("scratch/bom_output.csv"))
        with open("scratch/bom_output.csv", "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Quantity,Value,Library,References", content)
            self.assertIn("STM32", content)

    def test_langchain_tool_invocations(self):
        res1 = analyze_kicad_file.invoke({"file_path": self.test_file})
        self.assertIn("KiCad Analysis", res1)

        res2 = get_power_tree.invoke({"file_path": self.test_file})
        self.assertIn("AutoPick PCB Power Tree", res2)

        res3 = check_pcb_errors.invoke({"file_path": self.test_file})
        self.assertTrue(len(res3) > 0)


if __name__ == "__main__":
    unittest.main()
