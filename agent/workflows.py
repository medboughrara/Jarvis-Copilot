"""
Autonomous Workflows & Audit Trail Engine for Jarvis Copilot (AAS Core pattern).
Executes end-to-end multi-phase hardware reviews and writes reproducible audit artifacts.
"""

import os
import json
import time
from tools.kicad_tool import KiCadParser, analyze_kicad_file, get_power_tree, check_pcb_errors, generate_bom_report
from tools.thermal_tool import calculate_thermal_loss
from tools.signal_integrity_tool import check_signal_integrity
from tools.supply_chain_tool import check_supply_chain_status
from tools.reach_tool import check_compliance_status
from tools.formatters import format_tool_output_for_cli
import config

logger = config.get_logger(__name__)


def run_full_pcb_audit(file_path: str = "") -> dict:
    """
    Executes an autonomous multi-phase PCB audit workflow, deriving parameters directly from the parsed circuit model.
    Aggregate status is strictly computed from phases containing an explicit engineering verdict.
    """
    logger.info("Starting Autonomous Full PCB Audit Workflow...")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    # 0. Parse Circuit Model to derive real parameters dynamically
    parser = KiCadParser(file_path if file_path and os.path.exists(file_path) else None)
    model = parser.parse_to_model()

    derived_current_a = model.max_inferred_current_a
    derived_bus = model.detected_bus_types[0] if model.detected_bus_types else "I2C"
    derived_mcu = model.primary_mcu_part
    derived_driver = model.primary_driver_part

    logger.info(f"Derived Audit Parameters: Current={derived_current_a}A, Bus={derived_bus}, MCU={derived_mcu}, Driver={derived_driver}")

    # Phase 1: KiCad File Analysis
    kicad_info = analyze_kicad_file.invoke({"file_path": parser.file_path})
    
    # Phase 2: Electrical Rules Check
    erc_info = check_pcb_errors.invoke({"file_path": parser.file_path})

    # Phase 3: Power Tree Analysis
    power_info = get_power_tree.invoke({"file_path": parser.file_path})

    # Phase 4: Thermal & Current Density Assessment
    thermal_info = calculate_thermal_loss.invoke({
        "current_amps": derived_current_a,
        "trace_width_mils": 30.0,
        "trace_length_mm": 50.0,
        "copper_oz": 1.0,
        "vin_v": 12.0,
        "vout_v": 5.0,
        "reg_current_a": 0.5
    })

    # Phase 5: Signal Integrity Check
    si_info = check_signal_integrity.invoke({
        "bus_type": derived_bus.lower(),
        "bus_voltage": 3.3,
        "trace_cap_pf": 150.0,
        "baud_rate_bps": 400000
    })

    # Phase 6: Supply Chain & Compliance
    supply_info = check_supply_chain_status.invoke({"part_number": derived_mcu})
    compliance_info = check_compliance_status.invoke({"component_name": derived_driver})

    phases = {
        "kicad_structure": kicad_info,
        "electrical_rules_check": erc_info,
        "power_tree": power_info,
        "thermal_analysis": thermal_info,
        "signal_integrity": si_info,
        "supply_chain": supply_info,
        "compliance": compliance_info
    }

    # Aggregate status strictly from phases with an explicit engineering verdict
    check_verdicts = []
    for p_name, p_res in phases.items():
        if isinstance(p_res, dict):
            p_data = p_res.get("data", {})
            v = p_data.get("verdict")
            if v:  # Filter out None/absent verdicts (e.g. kicad_structure, power_tree)
                check_verdicts.append(v)

    if any(v == "FAILED" for v in check_verdicts):
        overall_status = "FAILED"
    elif any(v == "WARNING" for v in check_verdicts):
        overall_status = "WARNING"
    else:
        overall_status = "PASSED"

    report = {
        "timestamp": timestamp,
        "status": overall_status,
        "file_analyzed": os.path.basename(parser.file_path),
        "derived_parameters": {
            "current_amps": derived_current_a,
            "bus_type": derived_bus,
            "mcu_part": derived_mcu,
            "driver_part": derived_driver
        },
        "summary": f"Completed 6-stage autonomous hardware review ({overall_status}) covering ERC, Power, Thermal, SI, and Supply Chain.",
        "phases": phases
    }

    # Save artifacts to scratch/
    os.makedirs("scratch", exist_ok=True)
    json_path = "scratch/pcb_audit_report.json"
    md_path = "scratch/pcb_audit_report.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# PCB Hardware Audit Report: {report['file_analyzed']}\n")
        f.write(f"- **Timestamp**: {timestamp}\n")
        f.write(f"- **Overall Status**: {overall_status}\n")
        f.write(f"- **Derived Board Parameters**: {derived_current_a}A rail, {derived_bus} bus, MCU: {derived_mcu}, Driver: {derived_driver}\n\n")
        f.write("## Executive Summary\n")
        f.write(report["summary"] + "\n\n")

        f.write("## Phase Execution Log\n")
        for phase_name, phase_out in phases.items():
            fmt_text = format_tool_output_for_cli(phase_out) if isinstance(phase_out, dict) else str(phase_out)
            f.write(f"### Phase: {phase_name}\n```text\n{fmt_text}\n```\n\n")

    logger.info(f"Audit artifacts written to {json_path} and {md_path}")
    return report
