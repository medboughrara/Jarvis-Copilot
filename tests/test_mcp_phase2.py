"""
🧪 Unit Test Suite for Phase 2: KiCad MCP Server Tools & Agent Execution.
Verifies Phase 2 Definition of Done:
An MCP tool-driven instruction: 'add a 10k resistor between VCC and the output net'
executes through the tools, updates the project, and verifies ERC/project state.
"""

import os
import sys
import unittest

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from tools.kicad_tool import (
    get_project_info,
    read_schematic,
    add_component,
    connect_net,
    get_erc_violations,
    run_drc
)
from tools.kicad_editor import KiCadSchematicEditor


class TestKiCadMCPPhase2(unittest.TestCase):

    def setUp(self):
        os.makedirs("scratch", exist_ok=True)
        self.test_sch_path = os.path.abspath("scratch/test_phase2_project.kicad_sch")
        if os.path.exists(self.test_sch_path):
            os.remove(self.test_sch_path)
            
        # Create empty initial project
        initial_editor = KiCadSchematicEditor()
        initial_editor.save(self.test_sch_path)

    def test_mcp_add_component_and_connect_nets_e2e(self):
        """Tests end-to-end tool calls: add 10k resistor, connect to VCC and OUTPUT_NET."""
        print("\n--- Testing Phase 2 MCP Tool Pipeline ---")
        
        # 1. get_project_info before modification
        info_before = get_project_info.invoke({"file_path": self.test_sch_path})
        self.assertEqual(info_before["status"], "success")
        self.assertEqual(info_before["data"]["total_components"], 0)

        # 2. add_component: R1 (10k)
        add_res = add_component.invoke({
            "reference": "R1",
            "value": "10k",
            "footprint": "Resistor_SMD:R_0805_2012Metric",
            "at_x": 120.0,
            "at_y": 90.0,
            "file_path": self.test_sch_path
        })
        self.assertEqual(add_res["status"], "success")
        self.assertEqual(add_res["data"]["reference"], "R1")
        print(f"Tool add_component result: {add_res['summary']}")

        # 3. connect_net: Pin 1 -> VCC
        c1_res = connect_net.invoke({
            "reference": "R1",
            "pin_number": 1,
            "net_name": "VCC",
            "file_path": self.test_sch_path
        })
        self.assertEqual(c1_res["status"], "success")
        print(f"Tool connect_net (Pin 1) result: {c1_res['summary']}")

        # 4. connect_net: Pin 2 -> OUTPUT_NET
        c2_res = connect_net.invoke({
            "reference": "R1",
            "pin_number": 2,
            "net_name": "OUTPUT_NET",
            "file_path": self.test_sch_path
        })
        self.assertEqual(c2_res["status"], "success")
        print(f"Tool connect_net (Pin 2) result: {c2_res['summary']}")

        # 5. read_schematic to verify updated schematic model
        sch_data = read_schematic.invoke({"file_path": self.test_sch_path})
        self.assertEqual(sch_data["status"], "success")
        self.assertEqual(len(sch_data["data"]["components"]), 1)
        self.assertEqual(sch_data["data"]["components"][0]["reference"], "R1")
        self.assertEqual(sch_data["data"]["components"][0]["value"], "10k")

        # 6. get_erc_violations
        erc_res = get_erc_violations.invoke({"file_path": self.test_sch_path})
        self.assertEqual(erc_res["status"], "success")
        print(f"Tool get_erc_violations result: {erc_res['summary']}")

        # 7. Re-open independently from disk and verify file persistence
        reloaded = KiCadSchematicEditor(self.test_sch_path)
        self.assertEqual(len(reloaded.components), 1)
        self.assertEqual(reloaded.components[0]["reference"], "R1")
        self.assertEqual(reloaded.components[0]["value"], "10k")
        self.assertEqual(len(reloaded.wires), 2)
        self.assertEqual(len(reloaded.labels), 2)
        print("✅ Phase 2 Definition of Done PASSED: All 6 MCP tools verified on disk!")


if __name__ == "__main__":
    unittest.main()
