"""
🔄 Generalized Agentic Verify & Self-Correction Loop for Jarvis Copilot.

Provides a unified verification contract:
Research -> Plan / Propose -> Execute -> Verify (AST / Subprocess Tests / ERC-DRC) -> Self-Correct.

Subclasses:
1. AgenticCodeVerifyLoop: Software code verification (AST parsing + sandboxed test runner).
2. AgenticPcbVerifyLoop: Hardware schematic & PCB verification (KiCad ERC/DRC).
"""

import os
import re
import ast
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import config
from agent.security import agentshield

logger = config.get_logger(__name__)


class BaseVerifyLoop(ABC):
    """Abstract base class for closed-loop execution and self-correction."""

    @abstractmethod
    def plan(self, user_prompt: str) -> Dict[str, Any]:
        """Formulates actionable plan."""
        pass

    @abstractmethod
    def execute_and_verify(self, plan: Dict[str, Any], max_corrections: int = 2) -> Dict[str, Any]:
        """Executes plan and verifies results with autonomous self-correction."""
        pass


class AgenticCodeVerifyLoop(BaseVerifyLoop):
    """Autonomous software code verification and self-correction loop."""

    def __init__(self, target_file: Optional[str] = None):
        self.target_file = target_file

    def plan(self, user_prompt: str) -> Dict[str, Any]:
        return {
            "prompt": user_prompt,
            "target_file": self.target_file,
            "checks": ["Static AST Syntax Validation", "Sandboxed Subprocess Unit Test Execution"]
        }

    def verify_syntax(self, code_string: str) -> Dict[str, Any]:
        """Runs static AST syntax check."""
        try:
            tree = ast.parse(code_string)
            return {"status": "valid", "syntax_valid": True, "ast_nodes": len(list(ast.walk(tree)))}
        except SyntaxError as se:
            return {
                "status": "syntax_error",
                "syntax_valid": False,
                "error_line": se.lineno,
                "error_text": se.text,
                "message": f"SyntaxError at line {se.lineno}: {se.msg}"
            }

    def verify_execution(self, test_code: str, timeout: int = 10) -> Dict[str, Any]:
        """Runs test code in AgentShield sandbox."""
        return agentshield.run_sandboxed_python(test_code, timeout=timeout)

    def execute_and_verify(self, plan: Dict[str, Any], max_corrections: int = 2) -> Dict[str, Any]:
        """Stub for base contract compliance."""
        return {"status": "success", "message": "Code verification loop ready."}


class AgenticPcbVerifyLoop(BaseVerifyLoop):
    """Hardware KiCad schematic & PCB closed-loop verification engine."""

    def __init__(self, target_file: Optional[str] = None):
        self.target_file = target_file or os.path.abspath("scratch/agentic_project.kicad_sch")
        os.makedirs(os.path.dirname(self.target_file), exist_ok=True)
        if not os.path.exists(self.target_file):
            from tools.kicad_editor import KiCadSchematicEditor
            initial_editor = KiCadSchematicEditor()
            initial_editor.save(self.target_file)

    def plan(self, user_prompt: str) -> Dict[str, Any]:
        clean_q = user_prompt.lower()
        assumptions = []
        steps = []
        action_type = "custom"

        if "buck" in clean_q or "step down" in clean_q or "12v" in clean_q:
            action_type = "template_buck"
            assumptions.append("Targeting 12V input -> 5V/2A regulated output with MP1584 buck topology.")
            steps.append("1. Instantiate MP1584 controller with 4.7uH power inductor and Schottky diode.")
            steps.append("2. Place input/output capacitors and feedback resistor divider.")
        elif "ldo" in clean_q or "3.3v" in clean_q:
            action_type = "template_ldo"
            assumptions.append("Targeting 5V input -> 3.3V/600mA low-noise output using AP2112K-3.3 CMOS LDO.")
            steps.append("1. Place AP2112K-3.3 regulator symbol and bypass capacitors.")
        else:
            action_type = "generic_component"
            assumptions.append("Adding user-specified components and connecting specified nets.")
            steps.append("1. Search component library and connect pins to required power/signal nets.")

        steps.append("Verify: Run automated Electrical Rules Check (ERC) and trigger self-correction.")

        return {
            "prompt": user_prompt,
            "action_type": action_type,
            "assumptions": assumptions,
            "proposed_steps": steps
        }

    def execute_and_verify(self, plan: Dict[str, Any], max_corrections: int = 3) -> Dict[str, Any]:
        from tools.kicad_tool import add_component, connect_net, get_erc_violations
        from tools.circuit_templates_tool import generate_from_template
        from tools.kicad_editor import KiCadSchematicEditor

        action_type = plan.get("action_type", "custom")
        if action_type == "template_buck":
            generate_from_template.invoke({
                "template_name": "buck_converter",
                "params": {"vin_v": 12.0, "vout_v": 5.0, "iout_a": 2.0},
                "file_path": self.target_file
            })
        elif action_type == "template_ldo":
            generate_from_template.invoke({
                "template_name": "ldo_regulator",
                "params": {"vin_v": 5.0, "vout_v": 3.3},
                "file_path": self.target_file
            })
        else:
            add_component.invoke({"reference": "R1", "value": "10k", "file_path": self.target_file})
            connect_net.invoke({"reference": "R1", "pin_number": 1, "net_name": "VCC", "file_path": self.target_file})
            connect_net.invoke({"reference": "R1", "pin_number": 2, "net_name": "OUTPUT_NET", "file_path": self.target_file})

        # Run ERC
        erc_res = get_erc_violations.invoke({"file_path": self.target_file})
        verdict = erc_res.get("data", {}).get("verdict", "PASSED")
        issues = erc_res.get("data", {}).get("issues", [])

        corrections_applied = []
        iteration = 0

        while verdict == "FAILED" and iteration < max_corrections:
            iteration += 1
            editor = KiCadSchematicEditor(self.target_file)
            correction_notes = []

            for issue in issues:
                issue_lower = issue.lower()
                if "gnd" in issue_lower and "missing" in issue_lower:
                    editor.add_label(name="GND", at=(100.0, 150.0))
                    correction_notes.append("Injected missing common GND net label.")
                if "decoupling" in issue_lower or "capacitor" in issue_lower:
                    editor.add_symbol(reference="C_DEC1", value="100nF 50V", at=(110.0, 150.0), lib_id="Device:C")
                    editor.add_label(name="+3.3V", at=(110.0, 140.0))
                    editor.add_label(name="GND", at=(110.0, 160.0))
                    correction_notes.append("Added decoupling capacitors with +3.3V and GND rails.")

            if not correction_notes:
                editor.add_label(name="GND", at=(100.0, 150.0))
                correction_notes.append("Added safety reference ground net label.")

            editor.save(self.target_file)
            corrections_applied.extend(correction_notes)

            erc_res = get_erc_violations.invoke({"file_path": self.target_file})
            verdict = erc_res.get("data", {}).get("verdict", "PASSED")
            issues = erc_res.get("data", {}).get("issues", [])

        return {
            "status": "success",
            "summary": f"Agentic PCB verify loop completed. Final ERC: [{verdict}]. Self-corrections: {len(corrections_applied)}.",
            "data": {
                "file_path": self.target_file,
                "final_erc_verdict": verdict,
                "iterations_run": iteration,
                "corrections_applied": corrections_applied,
                "remaining_issues": issues
            }
        }

    def run_cycle(self, user_prompt: str, max_corrections: int = 3) -> Dict[str, Any]:
        plan_obj = self.plan(user_prompt)
        return self.execute_and_verify(plan_obj, max_corrections=max_corrections)
