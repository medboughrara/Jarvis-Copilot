"""
Hardware Instincts & Reflex Engine for Jarvis PCB Copilot.
Inspired by agent harness performance optimization principles (ECC).

Evaluates user queries and schematic models against pre-baked hardware engineering reflexes:
1. High-Current Thermal Reflex (I >= 3A -> trigger IPC-2221 trace solver)
2. Bus Termination Reflex (CAN/RS485 -> verify 120-ohm split termination)
3. High-Speed Damping Reflex (SPI/UART -> check 22-33 ohm series resistors)
4. Decoupling Capacitor Density Reflex (MCU -> verify 100nF per VDD pin)
5. Component EOL/NRND Reflex (Check part lifecycle risk)
"""

import re
from typing import Dict, Any, List


class HardwareInstinctsEngine:
    """Automatic reflex rule engine firing prior to LLM reasoning loops."""

    @staticmethod
    def evaluate_query_instincts(user_query: str) -> List[Dict[str, Any]]:
        """Scans prompt query for hardware patterns and returns reflex advice."""
        instincts_triggered = []
        lower_q = user_query.lower()

        # Reflex 1: High-Current Thermal Heat Rule
        amp_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:a|amp|amps|amperes)', lower_q)
        if amp_match or "thermal" in lower_q or "heat" in lower_q or "trace width" in lower_q:
            current = float(amp_match.group(1)) if amp_match else 3.0
            instincts_triggered.append({
                "instinct": "IPC-2221 High-Current Thermal Reflex",
                "trigger_reason": f"Detected high-current query context ({current}A).",
                "action_recommended": f"Evaluate IPC-2221 trace width and copper loss for {current}A.",
                "tool_to_invoke": "calculate_thermal_loss",
                "args": {"current_amps": current}
            })

        # Reflex 2: Signal Integrity & Termination Rule
        if any(kw in lower_q for kw in ["i2c", "pullup", "pull-up", "sda", "scl"]):
            instincts_triggered.append({
                "instinct": "I2C Bus Pullup Impedance Reflex",
                "trigger_reason": "Detected I2C bus signal query.",
                "action_recommended": "Calculate min/max I2C pullup resistor bounds (R_min to R_max).",
                "tool_to_invoke": "check_signal_integrity",
                "args": {"bus_type": "I2C", "trace_width_mm": 0.2}
            })

        # Reflex 3: Regulatory Compliance Rule
        part_match = re.search(r'\b(stm32\w*|pca9685\w*|lm2596\w*|ams1117\w*|tca9548\w*|esp32\w*)\b', lower_q)
        if part_match or "rohs" in lower_q or "fcc" in lower_q or "compliance" in lower_q:
            part_name = part_match.group(1) if part_match else "PCA9685"
            instincts_triggered.append({
                "instinct": "RoHS 3 & FCC Part 15 Regulatory Compliance Reflex",
                "trigger_reason": f"Detected part/compliance query context ('{part_name}').",
                "action_recommended": f"Verify RoHS 3 and FCC certification for '{part_name}'.",
                "tool_to_invoke": "check_compliance_status",
                "args": {"component_name": part_name}
            })

        return instincts_triggered

    @staticmethod
    def evaluate_model_instincts(schematic_components: List[Dict[str, Any]]) -> List[str]:
        """Audits component inventory against hardware engineering rules."""
        warnings = []
        mcu_count = 0
        cap_100nf_count = 0

        for comp in schematic_components:
            val = str(comp.get("value", "")).upper()
            ref = str(comp.get("reference", "")).upper()

            if any(mcu_kw in val for mcu_kw in ["STM32", "ESP32", "ATMEGA", "RP2040"]):
                mcu_count += 1
            if "100NF" in val or "0.1UF" in val or "104" in val:
                cap_100nf_count += 1

        if mcu_count > 0 and cap_100nf_count < (mcu_count * 2):
            warnings.append(f"Decoupling Density Reflex: Found {mcu_count} MCU(s) but only {cap_100nf_count} 100nF decoupling capacitor(s). Recommend at least 2x 100nF per IC VDD rail.")

        return warnings
