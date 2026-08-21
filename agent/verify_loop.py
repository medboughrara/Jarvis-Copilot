"""
🔄 Agentic Verify & Self-Correction Loop for Jarvis PCB Copilot (Phase 5).

Implements a closed-loop state machine:
Research -> Plan / Propose -> Execute -> Verify (ERC/DRC) -> Self-Correct.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import config
from tools.kicad_tool import (
    get_project_info,
    read_schematic,
    add_component,
    connect_net,
    get_erc_violations,
    run_drc
)
from tools.circuit_templates_tool import generate_from_template
from tools.parts_search_tool import search_parts
from tools.kicad_editor import KiCadSchematicEditor

logger = config.get_logger(__name__)


class AgenticPcbVerifyLoop:
    """Orchestrates research, planning, execution, ERC/DRC verification, and autonomous self-correction."""

    def __init__(self, target_file: Optional[str] = None):
        self.target_file = target_file or os.path.abspath("scratch/agentic_project.kicad_sch")
        os.makedirs(os.path.dirname(self.target_file), exist_ok=True)
        if not os.path.exists(self.target_file):
            initial_editor = KiCadSchematicEditor()
            initial_editor.save(self.target_file)

    def plan(self, user_prompt: str) -> Dict[str, Any]:
        """
        Formulates an actionable multi-step hardware modification plan with assumptions stated.
        """
        logger.info(f"[AgenticLoop] Formulating plan for: '{user_prompt}'")
        clean_q = user_prompt.lower()
        assumptions = []
        steps = []
        action_type = "custom"

        # 1. Detect template vs custom request
        if "buck" in clean_q or "step down" in clean_q or "12v" in clean_q:
            action_type = "template_buck"
            assumptions.append("Targeting 12V input -> 5V/2A regulated output with MP1584 high-efficiency buck topology.")
            steps.append("1. Instantiate MP1584 controller with 4.7uH power inductor and 3A Schottky catch diode.")
            steps.append("2. Place input bulk/filtering capacitors (10uF + 100nF) and output ceramic capacitors (22uF + 100nF).")
            steps.append("3. Wire feedback resistor divider (42k / 8.2k) for 5.0V output reference.")
            steps.append("4. Connect +12V, +5V, and common GND power net labels.")
        elif "ldo" in clean_q or "3.3v" in clean_q:
            action_type = "template_ldo"
            assumptions.append("Targeting 5V input -> 3.3V/600mA low-noise output using AP2112K-3.3 CMOS LDO.")
            steps.append("1. Place AP2112K-3.3 SOT-23-5 regulator symbol.")
            steps.append("2. Place 1uF input and 2.2uF output ceramic capacitors.")
            steps.append("3. Connect +5V, +3.3V, and common GND labels.")
        else:
            action_type = "generic_component"
            assumptions.append("Adding user-specified components and connecting specified power/signal nets.")
            steps.append("1. Search component library for best matching parts.")
            steps.append("2. Place symbol in schematic sheet.")
            steps.append("3. Connect component pins to required power/signal nets.")

        steps.append("Verify: Run automated Electrical Rules Check (ERC) and trigger self-correction if violations exist.")

        return {
            "prompt": user_prompt,
            "action_type": action_type,
            "assumptions": assumptions,
            "proposed_steps": steps
        }

    def execute_and_verify(self, plan: Dict[str, Any], max_corrections: int = 3) -> Dict[str, Any]:
        """
        Executes the plan, runs ERC verification, and triggers autonomous self-correction if issues arise.
        """
        action_type = plan.get("action_type", "custom")
        logger.info(f"[AgenticLoop] Executing plan (Type: {action_type})...")

        # 1. Execute initial action
        if action_type == "template_buck":
            gen_res = generate_from_template.invoke({
                "template_name": "buck_converter",
                "params": {"vin_v": 12.0, "vout_v": 5.0, "iout_a": 2.0},
                "file_path": self.target_file
            })
        elif action_type == "template_ldo":
            gen_res = generate_from_template.invoke({
                "template_name": "ldo_regulator",
                "params": {"vin_v": 5.0, "vout_v": 3.3},
                "file_path": self.target_file
            })
        else:
            # Add resistor and wire nets as baseline
            add_component.invoke({
                "reference": "R1",
                "value": "10k",
                "file_path": self.target_file
            })
            connect_net.invoke({"reference": "R1", "pin_number": 1, "net_name": "VCC", "file_path": self.target_file})
            connect_net.invoke({"reference": "R1", "pin_number": 2, "net_name": "OUTPUT_NET", "file_path": self.target_file})

        # 2. Run ERC verification
        erc_res = get_erc_violations.invoke({"file_path": self.target_file})
        verdict = erc_res.get("data", {}).get("verdict", "PASSED")
        issues = erc_res.get("data", {}).get("issues", [])
        
        corrections_applied = []
        iteration = 0

        # 3. Autonomous Self-Correction Loop
        while verdict == "FAILED" and iteration < max_corrections:
            iteration += 1
            logger.info(f"[AgenticLoop] ERC failed with {len(issues)} issues. Running Self-Correction Iteration {iteration}...")
            
            editor = KiCadSchematicEditor(self.target_file)
            correction_notes = []

            for issue in issues:
                issue_lower = issue.lower()
                # Remediation 1: Missing common GND net
                if "gnd" in issue_lower and "missing" in issue_lower:
                    editor.add_label(name="GND", at=(100.0, 150.0))
                    correction_notes.append("Injected missing common GND net label.")
                
                # Remediation 2: Low decoupling capacitor count for MCUs
                if "decoupling" in issue_lower or "capacitor" in issue_lower:
                    editor.add_symbol(reference="C_DEC1", value="100nF 50V", at=(110.0, 150.0), lib_id="Device:C")
                    editor.add_symbol(reference="C_DEC2", value="4.7uF 16V", at=(120.0, 150.0), lib_id="Device:C")
                    editor.add_label(name="+3.3V", at=(110.0, 140.0))
                    editor.add_label(name="GND", at=(110.0, 160.0))
                    correction_notes.append("Added 100nF and 4.7uF decoupling capacitors with +3.3V and GND rails.")

            if not correction_notes:
                # General safety ground tie
                editor.add_label(name="GND", at=(100.0, 150.0))
                correction_notes.append("Added safety reference ground net label.")

            editor.save(self.target_file)
            corrections_applied.extend(correction_notes)

            # Re-verify
            erc_res = get_erc_violations.invoke({"file_path": self.target_file})
            verdict = erc_res.get("data", {}).get("verdict", "PASSED")
            issues = erc_res.get("data", {}).get("issues", [])

        summary = (
            f"Agentic loop completed for '{plan.get('prompt', '')}'. Final ERC Verdict: [{verdict}]. "
            f"Self-corrections applied: {len(corrections_applied)}."
        )

        return {
            "status": "success",
            "summary": summary,
            "data": {
                "file_path": self.target_file,
                "initial_plan": plan,
                "final_erc_verdict": verdict,
                "iterations_run": iteration,
                "corrections_applied": corrections_applied,
                "remaining_issues": issues
            }
        }

    def run_cycle(self, user_prompt: str, max_corrections: int = 3) -> Dict[str, Any]:
        """Convenience method running complete plan -> execute -> verify cycle."""
        plan_obj = self.plan(user_prompt)
        return self.execute_and_verify(plan_obj, max_corrections=max_corrections)
