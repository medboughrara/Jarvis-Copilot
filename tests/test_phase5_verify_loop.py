"""
🧪 Unit Test Suite for Phase 5: Agentic Verify & Self-Correction Loop.
Verifies Phase 5 Definition of Done:
Given a request with an intentionally introduced ERC issue, the agent states its assumptions,
produces a plan, executes it, catches the ERC violation during verification, and self-corrects autonomously.
"""

import os
import sys
import unittest

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from agent.verify_loop import AgenticPcbVerifyLoop
from tools.kicad_editor import KiCadSchematicEditor


class TestVerifyLoopPhase5(unittest.TestCase):

    def setUp(self):
        os.makedirs("scratch", exist_ok=True)
        self.test_sch_path = os.path.abspath("scratch/test_phase5_loop.kicad_sch")
        if os.path.exists(self.test_sch_path):
            os.remove(self.test_sch_path)

    def test_plan_formulation_with_assumptions(self):
        """Tests that planning phase explicitly states assumptions and proposed steps."""
        print("\n--- Testing Phase 5: Plan Mode & Assumptions ---")
        loop = AgenticPcbVerifyLoop(self.test_sch_path)
        plan = loop.plan("Create a 5V buck converter for our board")
        
        self.assertGreater(len(plan["assumptions"]), 0)
        self.assertGreater(len(plan["proposed_steps"]), 0)
        print(f"Assumptions Stated: {plan['assumptions']}")
        print(f"Proposed Steps: {plan['proposed_steps']}")
        print("✅ Plan Mode & Assumptions Verified!")

    def test_self_correction_on_introduced_erc_violation(self):
        """Phase 5 Definition of Done: Catch introduced ERC violation and self-correct."""
        print("\n--- Testing Phase 5: Autonomous Self-Correction Loop ---")
        loop = AgenticPcbVerifyLoop(self.test_sch_path)
        
        # 1. Create a plan with generic component (initially missing GND rail to trigger ERC)
        plan = loop.plan("Add an MCU STM32F405 chip to schematic")
        
        # 2. Execute and run verification loop
        result = loop.execute_and_verify(plan, max_corrections=3)
        
        self.assertEqual(result["status"], "success")
        print(f"Loop Summary: {result['summary']}")
        print(f"Corrections Applied: {result['data']['corrections_applied']}")
        print(f"Final ERC Verdict: [{result['data']['final_erc_verdict']}]")
        
        # Verify self-correction was triggered and applied
        self.assertGreaterEqual(len(result["data"]["corrections_applied"]), 1)
        self.assertIn(result["data"]["final_erc_verdict"], ["PASSED", "WARNING"])
        
        # Reload schematic and verify that GND label and corrections were written to disk
        reloaded = KiCadSchematicEditor(self.test_sch_path)
        labels = [str(l[1]) for l in reloaded.labels if len(l) > 1]
        print(f"Persisted Labels in Corrected Schematic: {labels}")
        self.assertIn("GND", labels)
        print("✅ Phase 5 Definition of Done PASSED: Self-correction loop caught and fixed violation!")


if __name__ == "__main__":
    unittest.main()
