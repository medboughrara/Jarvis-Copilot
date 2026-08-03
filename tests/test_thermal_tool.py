"""
Unit tests for tools/thermal_tool.py (Jarvis PCB Copilot).
"""

import unittest
from tools.thermal_tool import calculate_thermal_loss

class TestThermalTool(unittest.TestCase):
    def test_calculate_thermal_loss(self):
        res = calculate_thermal_loss.invoke({
            "current_amps": 3.0,
            "trace_width_mils": 30.0,
            "trace_length_mm": 50.0,
            "copper_oz": 1.0,
            "vin_v": 12.0,
            "vout_v": 5.0,
            "reg_current_a": 0.5
        })
        self.assertIn("IPC-2221", res)
        self.assertIn("Trace Width: 30.0 mils", res)
        self.assertIn("Linear Regulator Drop: 12.0V -> 5.0V", res)

if __name__ == "__main__":
    unittest.main()
