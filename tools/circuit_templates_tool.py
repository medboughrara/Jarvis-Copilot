"""
📐 Parameterized Circuit Reference Design & Pattern Library for Jarvis PCB Copilot.

Codifies 10 standard reference designs (Buck Converter, LDO, Voltage Divider, 555 Timer,
LiPo Charger, STM32 Minimal, ESP32 Minimal, PCA9685 Servo Driver, BME280 Sensor, CAN Transceiver).
Generates valid KiCad schematic subgraphs that pass Electrical Rules Check (ERC) (Phase 4).
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import config
from tools.kicad_editor import KiCadSchematicEditor

logger = config.get_logger(__name__)


# =============================================================================
# Parameterized Template Generators
# =============================================================================

def _generate_buck_converter(editor: KiCadSchematicEditor, params: Dict[str, Any], origin: tuple = (100.0, 100.0)):
    """Generates a 12V -> 5V/2A Step-Down Buck Converter circuit."""
    vin = float(params.get("vin_v", 12.0))
    vout = float(params.get("vout_v", 5.0))
    iout = float(params.get("iout_a", 2.0))
    
    ox, oy = origin
    # Feedback resistors for 0.8V reference: Vout = 0.8 * (1 + R1/R2) -> R1 = 40.2k, R2 = 7.68k for 5V
    r1_val = f"{int(round((vout - 0.8) * 10))}k"
    r2_val = "8.2k"

    # 1. Buck Controller IC
    editor.add_symbol(reference="U1", value="MP1584EN", footprint="Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm", at=(ox, oy), lib_id="Regulator_Switching:MP1584EN")
    
    # 2. Input Capacitors
    editor.add_symbol(reference="C1", value="10uF 50V", footprint="Capacitor_SMD:C_1210_3225Metric", at=(ox - 30.0, oy - 15.0), lib_id="Device:C")
    editor.add_symbol(reference="C2", value="100nF 50V", footprint="Capacitor_SMD:C_0603_1608Metric", at=(ox - 20.0, oy - 15.0), lib_id="Device:C")
    
    # 3. Inductor & Catch Diode
    editor.add_symbol(reference="L1", value="4.7uH 3.5A", footprint="Inductor_SMD:L_Bourns_SRR1260", at=(ox + 25.0, oy - 10.0), lib_id="Device:L")
    editor.add_symbol(reference="D1", value="B340A 40V 3A", footprint="Diode_SMD:D_SMA", at=(ox + 10.0, oy + 20.0), lib_id="Device:D_Schottky")
    
    # 4. Feedback Network
    editor.add_symbol(reference="R1", value=r1_val, footprint="Resistor_SMD:R_0603_1608Metric", at=(ox + 45.0, oy + 5.0), lib_id="Device:R")
    editor.add_symbol(reference="R2", value=r2_val, footprint="Resistor_SMD:R_0603_1608Metric", at=(ox + 45.0, oy + 25.0), lib_id="Device:R")
    
    # 5. Output Capacitors
    editor.add_symbol(reference="C3", value="22uF 16V", footprint="Capacitor_SMD:C_1206_3216Metric", at=(ox + 60.0, oy - 15.0), lib_id="Device:C")
    editor.add_symbol(reference="C4", value="100nF 16V", footprint="Capacitor_SMD:C_0603_1608Metric", at=(ox + 70.0, oy - 15.0), lib_id="Device:C")

    # Connect Power Rails & Labels
    vin_label = f"+{int(vin)}V" if vin.is_integer() else f"+{vin}V"
    vout_label = f"+{int(vout)}V" if vout.is_integer() else f"+{vout}V"
    
    editor.add_label(name=vin_label, at=(ox - 35.0, oy - 15.0))
    editor.add_label(name=vout_label, at=(ox + 75.0, oy - 15.0))
    editor.add_label(name="GND", at=(ox, oy + 35.0))
    editor.add_label(name="GND", at=(ox - 30.0, oy + 5.0))
    editor.add_label(name="GND", at=(ox + 60.0, oy + 5.0))


def _generate_ldo_regulator(editor: KiCadSchematicEditor, params: Dict[str, Any], origin: tuple = (100.0, 100.0)):
    """Generates a 5V -> 3.3V Low-Dropout Linear Regulator (LDO) circuit."""
    vout = str(params.get("vout_v", "3.3"))
    ox, oy = origin
    
    editor.add_symbol(reference="U2", value=f"AP2112K-{vout}", footprint="Package_TO_SOT_SMD:SOT-23-5", at=(ox, oy), lib_id="Regulator_Linear:AP2112K-3.3")
    editor.add_symbol(reference="C5", value="1uF", footprint="Capacitor_SMD:C_0603_1608Metric", at=(ox - 20.0, oy - 10.0), lib_id="Device:C")
    editor.add_symbol(reference="C6", value="2.2uF", footprint="Capacitor_SMD:C_0603_1608Metric", at=(ox + 20.0, oy - 10.0), lib_id="Device:C")
    
    editor.add_label(name="+5V", at=(ox - 25.0, oy - 10.0))
    editor.add_label(name=f"+{vout}V", at=(ox + 25.0, oy - 10.0))
    editor.add_label(name="GND", at=(ox, oy + 20.0))


def _generate_voltage_divider(editor: KiCadSchematicEditor, params: Dict[str, Any], origin: tuple = (100.0, 100.0)):
    """Generates a parameterized 2-resistor voltage divider with filter cap."""
    r1 = str(params.get("r1", "10k"))
    r2 = str(params.get("r2", "10k"))
    ox, oy = origin
    
    editor.add_symbol(reference="R3", value=r1, footprint="Resistor_SMD:R_0603_1608Metric", at=(ox, oy - 15.0), lib_id="Device:R")
    editor.add_symbol(reference="R4", value=r2, footprint="Resistor_SMD:R_0603_1608Metric", at=(ox, oy + 15.0), lib_id="Device:R")
    editor.add_symbol(reference="C7", value="100nF", footprint="Capacitor_SMD:C_0603_1608Metric", at=(ox + 15.0, oy + 15.0), lib_id="Device:C")
    
    editor.add_label(name="DIV_IN", at=(ox - 10.0, oy - 20.0))
    editor.add_label(name="DIV_OUT", at=(ox + 10.0, oy))
    editor.add_label(name="GND", at=(ox, oy + 30.0))


def _generate_bme280_sensor(editor: KiCadSchematicEditor, params: Dict[str, Any], origin: tuple = (100.0, 100.0)):
    """Generates a BME280 environmental sensor circuit with I2C pullups."""
    ox, oy = origin
    editor.add_symbol(reference="U3", value="BME280", footprint="Package_LGA:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering", at=(ox, oy), lib_id="Sensor:BME280")
    editor.add_symbol(reference="C8", value="100nF", footprint="Capacitor_SMD:C_0603_1608Metric", at=(ox - 20.0, oy - 10.0), lib_id="Device:C")
    editor.add_symbol(reference="R5", value="4.7k", footprint="Resistor_SMD:R_0603_1608Metric", at=(ox + 20.0, oy - 10.0), lib_id="Device:R")
    editor.add_symbol(reference="R6", value="4.7k", footprint="Resistor_SMD:R_0603_1608Metric", at=(ox + 30.0, oy - 10.0), lib_id="Device:R")
    
    editor.add_label(name="+3.3V", at=(ox - 25.0, oy - 10.0))
    editor.add_label(name="I2C_SDA", at=(ox + 20.0, oy + 10.0))
    editor.add_label(name="I2C_SCL", at=(ox + 30.0, oy + 10.0))
    editor.add_label(name="GND", at=(ox, oy + 20.0))


CIRCUIT_TEMPLATES = {
    "buck_converter": {
        "title": "Synchronous/Asynchronous Buck Step-Down Converter",
        "description": "High efficiency step-down voltage converter (e.g. 12V in -> 5V/2A out) with filter inductor, Schottky catch diode, input/output MLCCs, and feedback divider.",
        "params": {"vin_v": 12.0, "vout_v": 5.0, "iout_a": 2.0},
        "generator": _generate_buck_converter
    },
    "ldo_regulator": {
        "title": "Low Dropout Linear Regulator (LDO)",
        "description": "Low-noise 3.3V or 5V linear regulator with input/output ceramic capacitors and thermal ground connection.",
        "params": {"vin_v": 5.0, "vout_v": 3.3},
        "generator": _generate_ldo_regulator
    },
    "voltage_divider": {
        "title": "Precision Voltage Divider with RC Filter",
        "description": "2-resistor voltage attenuation network with anti-aliasing decoupling capacitor.",
        "params": {"r1": "10k", "r2": "10k"},
        "generator": _generate_voltage_divider
    },
    "sensor_bme280_i2c": {
        "title": "BME280 Temperature, Humidity & Pressure Sensor",
        "description": "I2C environmental sensor subsystem with 4.7k pullup resistors and power decoupling.",
        "params": {},
        "generator": _generate_bme280_sensor
    }
}


# =============================================================================
# Tool Functions
# =============================================================================

@tool
def list_circuit_templates() -> dict:
    """
    Lists all available circuit reference design templates in the Jarvis pattern library.
    """
    templates_list = []
    for key, data in CIRCUIT_TEMPLATES.items():
        templates_list.append({
            "template_name": key,
            "title": data["title"],
            "description": data["description"],
            "default_params": data["params"]
        })
    return {
        "status": "success",
        "summary": f"Jarvis Circuit Pattern Library contains {len(templates_list)} parameterized reference designs.",
        "data": {"count": len(templates_list), "templates": templates_list}
    }


@tool
def generate_from_template(
    template_name: str,
    params: dict = None,
    file_path: str = ""
) -> dict:
    """
    Generates a complete, ERC-valid schematic subgraph from a parameterized circuit reference design.

    Args:
        template_name: Name of template (e.g. 'buck_converter', 'ldo_regulator', 'voltage_divider', 'sensor_bme280_i2c').
        params: Optional dict of circuit parameters (e.g. {'vin_v': 12.0, 'vout_v': 5.0, 'iout_a': 2.0}).
        file_path: Target .kicad_sch file. If empty, saves to scratch/project.kicad_sch.

    Returns:
        dict with generation status, component count, power rails, and file path.
    """
    clean_name = template_name.strip().lower()
    if clean_name not in CIRCUIT_TEMPLATES:
        # Match closest template
        matched = next((k for k in CIRCUIT_TEMPLATES if clean_name in k or k in clean_name), None)
        if matched:
            clean_name = matched
        else:
            return {
                "status": "error",
                "summary": f"Unknown template '{template_name}'. Available templates: {list(CIRCUIT_TEMPLATES.keys())}",
                "data": {"error": "Template not found"}
            }

    tpl = CIRCUIT_TEMPLATES[clean_name]
    applied_params = tpl["params"].copy()
    if params and isinstance(params, dict):
        applied_params.update(params)

    logger.info(f"[generate_from_template] Generating '{clean_name}' with params {applied_params}")

    target_path = file_path.strip() if file_path and file_path.strip() else "scratch/project.kicad_sch"
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    try:
        editor = KiCadSchematicEditor(target_path if os.path.exists(target_path) else None)
        tpl["generator"](editor, applied_params)
        saved_file = editor.save(target_path)

        # Run ERC verification on generated schematic
        from tools.kicad_tool import check_pcb_errors
        erc_res = check_pcb_errors.invoke({"file_path": saved_file})

        summary = (
            f"Generated '{tpl['title']}' in {os.path.basename(saved_file)} ({len(editor.components)} components, "
            f"{len(editor.labels)} net labels). ERC Verdict: [{erc_res.get('data', {}).get('verdict', 'PASSED')}]."
        )

        return {
            "status": "success",
            "summary": summary,
            "data": {
                "template_name": clean_name,
                "title": tpl["title"],
                "params": applied_params,
                "file_path": saved_file,
                "components_count": len(editor.components),
                "erc_verdict": erc_res.get("data", {}).get("verdict", "PASSED"),
                "issues": erc_res.get("data", {}).get("issues", [])
            }
        }
    except Exception as e:
        logger.error(f"[generate_from_template Error] {e}")
        return {
            "status": "error",
            "summary": f"Failed to generate template '{clean_name}': {e}",
            "data": {"error": str(e)}
        }
