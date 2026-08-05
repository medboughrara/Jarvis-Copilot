"""
Preferred Component Parts Library & Project Memory Tool for Jarvis PCB Copilot.
Stores and queries user-preferred JLCPCB basic parts, LDO regulators, microcontrollers, and passives.
"""

import os
import json
from typing import Dict, Any
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)
PARTS_FILE = os.path.join(os.getcwd(), "scratch", "preferred_parts_library.json")

DEFAULT_PARTS = {
    "microcontrollers": [
        {"mpn": "STM32F405RGT6", "package": "LQFP-64", "vendor": "STMicroelectronics", "notes": "168MHz ARM Cortex-M4, Dual CAN"},
        {"mpn": "ESP32-WROOM-32E", "package": "Module", "vendor": "Espressif", "notes": "Dual-Core WiFi/BLE, JLCPCB Basic"}
    ],
    "voltage_regulators": [
        {"mpn": "AMS1117-3.3", "package": "SOT-223", "vendor": "Advanced Monolithic", "notes": "3.3V 1A LDO, JLCPCB Basic"},
        {"mpn": "LM2596S-5.0", "package": "TO-263", "vendor": "Texas Instruments", "notes": "5V 3A Step-Down Buck Regulator"}
    ],
    "motor_drivers": [
        {"mpn": "PCA9685PW", "package": "TSSOP-28", "vendor": "NXP", "notes": "16-Channel 12-Bit PWM I2C Servo Driver"},
        {"mpn": "DRV8825PWPR", "package": "HTSSOP-28", "vendor": "Texas Instruments", "notes": "2.5A Stepper Motor Driver"}
    ],
    "passives": [
        {"mpn": "CL10B104KB8NNNC", "package": "0603", "vendor": "Samsung", "notes": "100nF 50V X7R Decoupling Capacitor, JLCPCB Basic"},
        {"mpn": "RC0603FR-0710KL", "package": "0603", "vendor": "Yageo", "notes": "10k 1% Resistor, JLCPCB Basic"}
    ]
}


def _load_parts() -> Dict[str, Any]:
    if os.path.exists(PARTS_FILE):
        try:
            with open(PARTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load preferred parts library: {e}")
    return DEFAULT_PARTS.copy()


def _save_parts(data: Dict[str, Any]):
    os.makedirs(os.path.dirname(PARTS_FILE), exist_ok=True)
    with open(PARTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@tool
def manage_preferred_parts(
    action: str = "list",
    category: str = "passives",
    part_number: str = "",
    notes: str = ""
) -> dict:
    """
    Manages preferred component library parts (list, add, or query).
    Actions: 'list', 'add', 'query'. Categories: 'microcontrollers', 'voltage_regulators', 'motor_drivers', 'passives'.
    """
    try:
        parts_db = _load_parts()
        action_lower = action.lower().strip()

        if action_lower == "list":
            summary_lines = ["[Preferred Component Library Memory]:"]
            for cat, items in parts_db.items():
                mpns = [item["mpn"] for item in items]
                summary_lines.append(f"  - {cat.capitalize()}: {', '.join(mpns)}")

            return {
                "status": "success",
                "summary": "\n".join(summary_lines),
                "data": parts_db
            }

        elif action_lower == "add":
            if not part_number:
                return {"status": "error", "summary": "part_number parameter is required for 'add' action."}

            cat_key = category.lower().strip()
            if cat_key not in parts_db:
                parts_db[cat_key] = []

            new_entry = {"mpn": part_number.upper(), "notes": notes or "User preferred component"}
            parts_db[cat_key].append(new_entry)
            _save_parts(parts_db)

            return {
                "status": "success",
                "summary": f"Saved '{part_number.upper()}' to preferred '{cat_key}' library memory.",
                "data": new_entry
            }

        elif action_lower == "query":
            q_term = part_number.upper().strip()
            matches = []
            for cat, items in parts_db.items():
                for item in items:
                    if q_term in item["mpn"].upper() or q_term in item.get("notes", "").upper():
                        matches.append(item)

            if matches:
                match_str = ", ".join([f"{m['mpn']} ({m.get('notes', '')})" for m in matches])
                return {
                    "status": "success",
                    "summary": f"Found {len(matches)} matching preferred part(s): {match_str}",
                    "data": {"matches": matches}
                }
            else:
                return {
                    "status": "success",
                    "summary": f"No exact match for '{q_term}' in preferred parts library. Recommending standard JLCPCB basic parts.",
                    "data": {"matches": []}
                }

        else:
            return {"status": "error", "summary": f"Unknown action '{action}'. Use 'list', 'add', or 'query'."}

    except Exception as e:
        logger.error(f"[manage_preferred_parts Error] {e}")
        return {
            "status": "error",
            "summary": f"Error managing preferred parts: {e}",
            "data": {"error": str(e)}
        }
