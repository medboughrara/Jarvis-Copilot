"""
Unit tests for tools/signal_integrity_tool.py (Jarvis PCB Copilot).
"""

import unittest
from tools.signal_integrity_tool import check_signal_integrity

class TestSignalIntegrityTool(unittest.TestCase):
    def test_i2c_pullup_calculation(self):
        res = check_signal_integrity.invoke({
            "bus_type": "i2c",
            "bus_voltage": 3.3,
            "trace_cap_pf": 150.0,
            "baud_rate_bps": 400000
        })
        self.assertEqual(res["status"], "success")
        self.assertIn("verdict", res["data"])
        self.assertEqual(res["data"]["bus_type"], "I2C")

    def test_uart_damping_recommendation(self):
        res = check_signal_integrity.invoke({"bus_type": "uart"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["bus_type"], "UART")

    def test_can_termination_recommendation(self):
        res = check_signal_integrity.invoke({"bus_type": "can"})
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data"]["bus_type"], "CAN")

if __name__ == "__main__":
    unittest.main()
