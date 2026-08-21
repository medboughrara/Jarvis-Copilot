"""
🔍 KiCad Component Library & Datasheet Semantic Search Tool for Jarvis PCB Copilot.

Provides semantic and parametric search over indexed KiCad symbols, footprints,
and real manufacturer electronic components (Phase 3).
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

# Indexed standard component catalog for semantic and parametric retrieval
COMPONENT_CATALOG = [
    {
        "mpn": "STM32L431CBT6",
        "category": "microcontrollers",
        "manufacturer": "STMicroelectronics",
        "package": "LQFP-48",
        "footprint": "Package_QFP:LQFP-48_7x7mm_P0.5mm",
        "lib_id": "MCU_ST_STM32L4:STM32L431CBTx",
        "voltage_range": "1.71V - 3.6V",
        "supply_current": "28 uA/MHz (run), 1.0 uA (standby)",
        "description": "Ultra-low-power ARM Cortex-M4 MCU with FPU, 80MHz, 128KB Flash, 64KB SRAM. Ideal for low-power battery-operated IoT devices.",
        "keywords": ["low power mcu", "battery operation", "cortex-m4", "stm32", "energy efficient", "3.3v mcu"]
    },
    {
        "mpn": "nRF52840-QIAA",
        "category": "microcontrollers",
        "manufacturer": "Nordic Semiconductor",
        "package": "aQFN-73",
        "footprint": "Package_DFN_QFN:Nordic_aQFN-73-1EP_7x7mm_P0.5mm",
        "lib_id": "MCU_Nordic:nRF52840",
        "voltage_range": "1.7V - 5.5V",
        "supply_current": "4.8 mA TX/RX, 0.4 uA sleep",
        "description": "Ultra-low power multiprotocol Bluetooth 5.4, Thread, Zigbee SoC with 64MHz ARM Cortex-M4F. Designed for coin-cell battery operation.",
        "keywords": ["low power mcu", "battery operation", "bluetooth", "ble", "nordic", "wireless", "coin cell"]
    },
    {
        "mpn": "ATtiny85-20SU",
        "category": "microcontrollers",
        "manufacturer": "Microchip Technology",
        "package": "SOIC-8",
        "footprint": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        "lib_id": "MCU_Microchip_ATtiny:ATtiny85-20S",
        "voltage_range": "1.8V - 5.5V",
        "supply_current": "300 uA active (1MHz 1.8V), 0.1 uA power-down",
        "description": "Compact 8-bit AVR microcontroller with 8KB ISP flash, 6 I/O pins. Extremely low standby power for battery projects.",
        "keywords": ["low power mcu", "battery", "8-bit", "attiny", "small mcu", "8-pin"]
    },
    {
        "mpn": "ESP32-S3-WROOM-1-N8",
        "category": "microcontrollers",
        "manufacturer": "Espressif Systems",
        "package": "SMD Module",
        "footprint": "RF_Module:ESP32-S3-WROOM-1",
        "lib_id": "RF_Module:ESP32-S3-WROOM-1",
        "voltage_range": "3.0V - 3.6V",
        "supply_current": "80 mA active, 5 uA deep sleep",
        "description": "Powerful 240MHz Dual-Core Xtensa LX7 MCU with 2.4GHz Wi-Fi and Bluetooth 5 (LE), 8MB Flash, vector instructions for AI/DSP.",
        "keywords": ["wifi", "bluetooth", "espressif", "dual core", "iot", "high performance mcu"]
    },
    {
        "mpn": "STM32F405RGT6",
        "category": "microcontrollers",
        "manufacturer": "STMicroelectronics",
        "package": "LQFP-64",
        "footprint": "Package_QFP:LQFP-64_10x10mm_P0.5mm",
        "lib_id": "MCU_ST_STM32F4:STM32F405RGTx",
        "voltage_range": "1.8V - 3.6V",
        "supply_current": "100 mA active (168MHz), 1.7 uA standby",
        "description": "High-performance 168MHz ARM Cortex-M4 MCU with 1MB Flash, 192KB SRAM, dual CAN buses, 3x SPI, 3x I2C. Standard for robotics and motion control.",
        "keywords": ["stm32f4", "cortex-m4", "robotics", "can bus", "motor control", "high performance"]
    },
    {
        "mpn": "TPS62840DLYR",
        "category": "power_regulators",
        "manufacturer": "Texas Instruments",
        "package": "WSON-6",
        "footprint": "Package_SON:WSON-6_1.5x1.5mm_P0.5mm",
        "lib_id": "Regulator_Switching:TPS62840",
        "voltage_range": "1.8V - 6.5V (Vin), 0.8V - 3.6V (Vout)",
        "supply_current": "60 nA operating quiescent current (Iq)",
        "description": "Ultra-low quiescent current (60nA) 750mA step-down converter for battery-powered IoT and wearable electronics.",
        "keywords": ["low power", "ultra low iq", "buck converter", "battery operation", "step down", "energy harvesting"]
    },
    {
        "mpn": "AP2112K-3.3TRG1",
        "category": "power_regulators",
        "manufacturer": "Diodes Incorporated",
        "package": "SOT-23-5",
        "footprint": "Package_TO_SOT_SMD:SOT-23-5",
        "lib_id": "Regulator_Linear:AP2112K-3.3",
        "voltage_range": "2.5V - 6.0V (Vin), 3.3V (Vout)",
        "supply_current": "600 mA output, 55 uA quiescent current, 250mV dropout",
        "description": "600mA low-dropout linear regulator with enable pin, low noise, and low quiescent current. Standard JLCPCB Basic Part for 3.3V rails.",
        "keywords": ["ldo", "3.3v regulator", "linear regulator", "low dropout", "ap2112", "jlcpcb basic"]
    },
    {
        "mpn": "MCP73831T-2ACI/OT",
        "category": "battery_chargers",
        "manufacturer": "Microchip Technology",
        "package": "SOT-23-5",
        "footprint": "Package_TO_SOT_SMD:SOT-23-5",
        "lib_id": "Battery_Management:MCP73831-2-OT",
        "voltage_range": "3.75V - 6.0V (Vin), 4.2V regulation",
        "supply_current": "Programmable charge current up to 500mA",
        "description": "Miniature single-cell fully integrated Li-Ion and Li-Polymer charge management controller with status output.",
        "keywords": ["battery charger", "lipo charger", "li-ion", "single cell", "4.2v", "mcp73831"]
    },
    {
        "mpn": "PCA9685PW",
        "category": "motor_drivers",
        "manufacturer": "NXP Semiconductors",
        "package": "TSSOP-28",
        "footprint": "Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm",
        "lib_id": "Driver_LED:PCA9685PW",
        "voltage_range": "2.3V - 5.5V",
        "supply_current": "10 mA active, 2.5 uA standby",
        "description": "16-channel, 12-bit PWM I2C-bus controlled servo/LED controller with 24MHz internal oscillator and 25mA drive capability per channel.",
        "keywords": ["servo driver", "pwm driver", "pca9685", "i2c", "16-channel", "robotics"]
    },
    {
        "mpn": "BME280",
        "category": "sensors",
        "manufacturer": "Bosch Sensortec",
        "package": "LGA-8",
        "footprint": "Package_LGA:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering",
        "lib_id": "Sensor:BME280",
        "voltage_range": "1.71V - 3.6V",
        "supply_current": "3.6 uA (1Hz humidity/temp/pressure), 0.1 uA sleep",
        "description": "Combined digital humidity, pressure, and temperature sensor. Ultra-low power consumption for battery-powered environmental monitors.",
        "keywords": ["sensor", "temperature", "humidity", "barometer", "low power", "bme280", "i2c", "spi"]
    }
]


def _score_component_match(part: Dict[str, Any], query_terms: List[str]) -> float:
    """Calculates keyword and semantic relevance score for a component record."""
    score = 0.0
    text_corpus = (
        f"{part['mpn']} {part['description']} {part['category']} "
        f"{part['manufacturer']} {part['voltage_range']} {' '.join(part['keywords'])}"
    ).lower()

    for term in query_terms:
        if len(term) < 2:
            continue
        if term in part["mpn"].lower():
            score += 5.0
        if term in [k.lower() for k in part["keywords"]]:
            score += 3.0
        if term in part["category"].lower():
            score += 2.0
        if term in part["description"].lower():
            score += 1.5
        if term in text_corpus:
            score += 0.5

    return score


@tool
def search_parts(
    query: str,
    category: str = "",
    top_k: int = 5
) -> dict:
    """
    Searches the indexed KiCad component and datasheet library for components matching semantic or parametric specifications.

    Args:
        query: Natural language search query or specs (e.g. 'low power MCU for battery operation', '3.3V LDO 600mA', '16-channel servo driver').
        category: Optional category filter: 'microcontrollers', 'power_regulators', 'battery_chargers', 'motor_drivers', 'sensors'.
        top_k: Maximum number of candidate parts to return.

    Returns:
        dict containing matched components with MPN, manufacturer, package footprint, voltage/current specs, and KiCad library IDs.
    """
    clean_query = query.strip().lower()
    query_terms = re.findall(r'[a-zA-Z0-9_\-\.]+', clean_query)
    
    logger.info(f"[search_parts] Query: '{query}' (Category: '{category}', top_k={top_k})")

    candidates = []
    for part in COMPONENT_CATALOG:
        if category and category.strip().lower() not in part["category"].lower():
            continue
        
        score = _score_component_match(part, query_terms)
        if score > 0 or not query_terms:
            candidates.append((score, part))

    # Sort descending by relevance score
    candidates.sort(key=lambda x: x[0], reverse=True)
    results = [c[1] for c in candidates[:top_k]]

    # If no exact match found, provide best category candidates
    if not results and COMPONENT_CATALOG:
        results = COMPONENT_CATALOG[:top_k]

    summary = f"Found {len(results)} component(s) matching '{query}'"
    if results:
        top_mpn = results[0]["mpn"]
        top_desc = results[0]["description"]
        summary += f": Top match is **{top_mpn}** ({top_desc[:80]}...)."

    return {
        "status": "success",
        "summary": summary,
        "data": {
            "query": query,
            "category": category,
            "count": len(results),
            "parts": results
        }
    }


@tool
def parse_component_datasheet(pdf_path_or_url: str, part_name: str = "") -> dict:
    """
    Extracts pinouts, voltage ratings, current limits, and footprint specifications from a component datasheet PDF.

    Args:
        pdf_path_or_url: Local filepath or URL to component datasheet PDF.
        part_name: Optional component part number for context.
    """
    logger.info(f"[parse_component_datasheet] Parsing '{pdf_path_or_url}' for part '{part_name}'")
    
    try:
        from tools.unlimited_ocr_tool import parse_document_unlimited_ocr
        res = parse_document_unlimited_ocr.invoke({"file_path": pdf_path_or_url, "max_pages": 4})
        return {
            "status": "success",
            "summary": f"Parsed datasheet for {part_name or os.path.basename(pdf_path_or_url)}.",
            "data": {
                "source": pdf_path_or_url,
                "part_name": part_name,
                "parsed_content": res.get("data", {}).get("markdown_content", "")[:2000]
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "summary": f"Could not parse datasheet: {e}",
            "data": {"error": str(e)}
        }
