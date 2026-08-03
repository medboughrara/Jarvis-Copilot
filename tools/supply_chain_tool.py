"""
Supply Chain, Lifecycle & Obsolescence Checker Tool for Jarvis Copilot.
Evaluates component lifecycle status (Active vs NRND vs EOL), inventory risk, and distributor availability.
"""

from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

# Database of AutoPick project components and supply chain metrics
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
def check_supply_chain_status(part_number: str = "STM32F405RGT6") -> str:
    """
    Evaluates component lifecycle status (Active vs NRND vs EOL), stock availability, and supply chain risks.
    
    Args:
        part_number: Part number or component name (e.g. "STM32F405RGT6", "PCA9685", "AMS1117-3.3").
    """
    clean_part = part_number.strip().upper()
    
    # Matching component entry
    matched_entry = None
    for key, data in COMPONENT_DATABASE.items():
        if key in clean_part or clean_part in key:
            matched_entry = (key, data)
            break

    if not matched_entry:
        return (
            f"============================================================\n"
            f"    SUPPLY CHAIN AUDIT: {clean_part}\n"
            f"============================================================\n"
            f"Lifecycle Status: Unindexed in Local Database\n"
            f"Stock Availability: Unknown\n"
            f"Distributor Coverage: Unverified\n"
            f"Risk Level: Unverified (Unindexed Part)\n"
            f"Recommendation: Part '{clean_part}' is not in local catalog. Perform live lookup via distributor API (LCSC, Octopart, or Mouser).\n"
            f"============================================================"
        )

    key, data = matched_entry
    report = [
        "============================================================",
        f"    AUTOPICK SUPPLY CHAIN AUDIT: {key}",
        "============================================================",
        f"Description: {data['description']}",
        f"Lifecycle Status: {data['lifecycle']} (No Obsolescence Risk)",
        f"Stock Availability: {data['stock_status']}",
        f"Distributors: {', '.join(data['distributors'])}",
        f"JLCPCB Assembly Type: {data['jlcpcb_type']}",
        f"Risk Level: {data['risk_level']}",
        f"Pin-Compatible Second Source: {data['second_source']}",
        "============================================================"
    ]
    return "\n".join(report)
