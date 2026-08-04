"""
Supply Chain, Lifecycle & Obsolescence Checker Tool for Jarvis Copilot.
Evaluates component lifecycle status (Active vs NRND vs EOL), inventory risk, and distributor availability.
Returns structured dictionaries adhering to the {status, data, summary} contract.
"""

from typing import Dict, Any
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

COMPONENT_DATABASE = {
    "STM32F405RGT6": {
        "description": "ARM Cortex-M4 32-bit MCU 168MHz 1MB Flash LQFP-64",
        "lifecycle": "Active",
        "stock_status": "In Stock (High Volume)",
        "distributors": ["LCSC", "Mouser", "DigiKey", "Element14"],
        "jlcpcb_type": "Extended Part",
        "risk_level": "Low Risk",
        "second_source": "STM32F407RGT6 (Pin Compatible)"
    },
    "PCA9685": {
        "description": "16-channel 12-bit PWM I2C Servo Driver TSSOP-28",
        "lifecycle": "Active",
        "stock_status": "In Stock",
        "distributors": ["LCSC", "Mouser", "DigiKey"],
        "jlcpcb_type": "Basic Part",
        "risk_level": "Low Risk",
        "second_source": "TCA9548A / NXP PCA9685PW"
    },
    "AMS1117-3.3": {
        "description": "800mA Low Dropout Linear Voltage Regulator SOT-223",
        "lifecycle": "Active",
        "stock_status": "Abundant",
        "distributors": ["LCSC", "JLCPCB", "Mouser"],
        "jlcpcb_type": "Basic Part",
        "risk_level": "Lowest Risk",
        "second_source": "LM1117-3.3, MP2307"
    },
    "MG996R": {
        "description": "High-Torque Metal Gear Digital Servomotor 11kg-cm",
        "lifecycle": "Active",
        "stock_status": "In Stock (Global Hobby & Industrial Distributors)",
        "distributors": ["TowerPro", "LCSC", "Amazon", "AliExpress"],
        "jlcpcb_type": "Off-Board Connector J1",
        "risk_level": "Low Risk",
        "second_source": "STS3215, SG90"
    }
}


@tool
def check_supply_chain_status(part_number: str = "STM32F405RGT6") -> dict:
    """
    Evaluates component lifecycle status (Active vs NRND vs EOL), stock availability, and supply chain risks.
    """
    try:
        clean_part = part_number.strip().upper()

        matched_entry = None
        for key, data in COMPONENT_DATABASE.items():
            if key in clean_part or clean_part in key:
                matched_entry = (key, data)
                break

        if not matched_entry:
            verdict = "WARNING"
            summary_str = f"Supply Chain Audit for '{clean_part}': Verdict [{verdict}] | Unindexed in local catalog. Perform live lookup."
            return {
                "status": "success",
                "summary": summary_str,
                "data": {
                    "verdict": verdict,
                    "part_number": clean_part,
                    "lifecycle": "Unindexed",
                    "stock_status": "Unknown",
                    "risk_level": "Unverified"
                }
            }

        key, data = matched_entry
        lifecycle = data["lifecycle"]
        if lifecycle == "Active":
            verdict = "PASSED"
        elif lifecycle == "NRND":
            verdict = "WARNING"
        else: # EOL
            verdict = "FAILED"

        summary_str = f"Supply Chain Audit for '{key}': Verdict [{verdict}] | Lifecycle: {lifecycle}, Stock: {data['stock_status']}, Risk: {data['risk_level']}."

        return {
            "status": "success",
            "summary": summary_str,
            "data": {
                "verdict": verdict,
                "part_number": key,
                "description": data["description"],
                "lifecycle": lifecycle,
                "stock_status": data["stock_status"],
                "distributors": data["distributors"],
                "jlcpcb_type": data["jlcpcb_type"],
                "risk_level": data["risk_level"],
                "second_source": data["second_source"]
            }
        }
    except Exception as e:
        logger.error(f"[check_supply_chain_status Error] {e}")
        return {
            "status": "error",
            "summary": f"Error checking supply chain status: {e}",
            "data": {"verdict": "FAILED", "error": str(e)}
        }
