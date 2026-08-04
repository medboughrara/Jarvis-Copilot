"""
Native Stdio Model Context Protocol (MCP) Server for Jarvis PCB Copilot.
Exposes KiCad, ERC, BOM, OmniParser, Thermal, Signal Integrity, and Supply Chain tools to agentic IDEs.
"""

from fastmcp import FastMCP
import config
from tools.kicad_tool import analyze_kicad_file, get_power_tree, check_pcb_errors, generate_bom_report
from tools.reach_tool import search_component_datasheet, check_compliance_status
from tools.omniparser_tool import parse_screen_gui
from tools.datasheet_rag_tool import query_local_datasheets
from tools.thermal_tool import calculate_thermal_loss
from tools.signal_integrity_tool import check_signal_integrity
from tools.supply_chain_tool import check_supply_chain_status
from tools.github_tool import manage_github_issue
from tools.doc_exporter_tool import export_engineering_doc
from tools.nvidia_nim_tool import generate_nvidia_image, run_nvidia_reasoning, parse_nemotron_ocr
from agent.workflows import run_full_pcb_audit

logger = config.get_logger(__name__)

# Initialize FastMCP Server
mcp = FastMCP(
    name="Jarvis-PCB-Copilot",
    instructions="Local hardware copilot for KiCad schematic review, IPC-2221 thermal loss, signal integrity, and servomotor compliance."
)

@mcp.tool()
def kicad_analyze(file_path: str = "") -> str:
    """Parses KiCad .kicad_sch or .kicad_pcb file and extracts component count, nets, and schematic structure."""
    return analyze_kicad_file.invoke({"file_path": file_path})

@mcp.tool()
def power_tree_generate(file_path: str = "") -> str:
    """Generates power distribution rail hierarchy (e.g. 12V -> 5V -> 3.3V) for KiCad schematic."""
    return get_power_tree.invoke({"file_path": file_path})

@mcp.tool()
def erc_check(file_path: str = "") -> str:
    """Runs automated Electrical Rules Check (ERC) for missing decoupling capacitors or floating nets."""
    return check_pcb_errors.invoke({"file_path": file_path})

@mcp.tool()
def bom_generate(file_path: str = "") -> str:
    """Generates grouped Bill of Materials (BOM) CSV report outputting to scratch/bom_output.csv."""
    return generate_bom_report.invoke({"file_path": file_path})

@mcp.tool()
def datasheet_lookup(query: str) -> str:
    """Searches live component datasheet database for motor specs, pinouts, and electrical limits."""
    return search_component_datasheet.invoke({"query": query})

@mcp.tool()
def compliance_check(component_name: str) -> str:
    """Checks RoHS 3 (2015/863/EU) lead-free and FCC Part 15 Class B compliance status."""
    return check_compliance_status.invoke({"component_name": component_name})

@mcp.tool()
def screen_gui_parse(action_context: str = "") -> str:
    """Captures active screen display monitor and runs OmniParser V2 + RapidOCR layout detection."""
    return parse_screen_gui.invoke({"action_context": action_context})

@mcp.tool()
def pdf_datasheet_rag(query: str) -> str:
    """Queries local ChromaDB vector store for technical documentation stored in datasheets/."""
    return query_local_datasheets.invoke({"query": query})

@mcp.tool()
def thermal_loss_calculate(
    current_amps: float = 3.0,
    trace_width_mils: float = 30.0,
    trace_length_mm: float = 50.0,
    copper_oz: float = 1.0,
    vin_v: float = 12.0,
    vout_v: float = 5.0,
    reg_current_a: float = 0.5
) -> str:
    """Calculates IPC-2221 trace width, copper I^2R power loss, and linear regulator thermal dissipation."""
    return calculate_thermal_loss.invoke({
        "current_amps": current_amps,
        "trace_width_mils": trace_width_mils,
        "trace_length_mm": trace_length_mm,
        "copper_oz": copper_oz,
        "vin_v": vin_v,
        "vout_v": vout_v,
        "reg_current_a": reg_current_a
    })

@mcp.tool()
def signal_integrity_check(
    bus_type: str = "i2c",
    bus_voltage: float = 3.3,
    trace_cap_pf: float = 150.0,
    baud_rate_bps: int = 400000
) -> str:
    """Calculates I2C pull-up resistor bounds, UART damping resistors, and CAN bus termination."""
    return check_signal_integrity.invoke({
        "bus_type": bus_type,
        "bus_voltage": bus_voltage,
        "trace_cap_pf": trace_cap_pf,
        "baud_rate_bps": baud_rate_bps
    })

@mcp.tool()
def supply_chain_check(part_number: str = "STM32F405RGT6") -> str:
    """Evaluates component lifecycle status (Active vs NRND vs EOL), stock availability, and distributor coverage."""
    return check_supply_chain_status.invoke({"part_number": part_number})

@mcp.tool()
def pcb_full_audit_workflow(file_path: str = "") -> str:
    """Runs autonomous 6-stage hardware review and outputs JSON/Markdown audit artifacts to scratch/."""
    res = run_full_pcb_audit(file_path)
    return f"Audit completed successfully. Status: {res['status']}. Report saved to scratch/pcb_audit_report.md"

@mcp.tool()
def github_issue_log(title: str, body: str, labels: str = "hardware-erc") -> str:
    """Logs a GitHub issue/ticket for PCB schematic errors, thermal alerts, or component risks."""
    return manage_github_issue.invoke({"title": title, "body": body, "labels": labels})

@mcp.tool()
def doc_export(title: str, content: str, format_type: str = "markdown") -> str:
    """Exports structured engineering log reports to docs/ directory."""
    return export_engineering_doc.invoke({"title": title, "content": content, "format_type": format_type})

@mcp.tool()
def nvidia_image_gen(prompt: str, width: int = 1024, height: int = 1024) -> str:
    """Generates high-resolution concept images or PCB block diagrams using NVIDIA FLUX.1-Schnell foundation model."""
    return generate_nvidia_image.invoke({"prompt": prompt, "width": width, "height": height})

@mcp.tool()
def nvidia_reasoning(query: str, model_choice: str = "kimi-k2.6") -> str:
    """Executes deep hardware reasoning and architectural analysis using Moonshot Kimi 2.6 or NVIDIA Nemotron 3 Reasoning models."""
    return run_nvidia_reasoning.invoke({"query": query, "model_choice": model_choice})

@mcp.tool()
def nvidia_nemotron_ocr(image_path: str = "") -> str:
    """Extracts text, table values, component designations, and pinouts from PCB screenshots or PDF datasheets using NVIDIA Nemotron OCR v2."""
    return parse_nemotron_ocr.invoke({"image_path": image_path})

if __name__ == "__main__":
    logger.info("Starting Jarvis PCB Copilot Stdio MCP Server...")
    mcp.run(transport="stdio")
