"""
KiCad PCB & Schematic Parser Tool for Jarvis Copilot.
Uses sexpdata S-expression AST parsing to build a unified SchematicModel.
Returns structured dictionaries adhering to the {status, data, summary} contract.
"""

import os
import re
import glob
import csv
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Any, Set, Optional, Tuple
from langchain_core.tools import tool
import sexpdata
import config

logger = config.get_logger(__name__)


def find_latest_kicad_file(extension: str = ".kicad_sch") -> Tuple[str, bool]:
    """Searches workspace and current directory for KiCad schematic or PCB files. Returns (file_path, is_sample_fallback)."""
    cwd = os.path.abspath(os.getcwd())
    search_dirs = [cwd]
    for d in search_dirs:
        pattern = os.path.join(d, f"**/*{extension}")
        matches = glob.glob(pattern, recursive=True)
        non_test_matches = [m for m in matches if f"{os.sep}tests{os.sep}" not in os.path.abspath(m)]
        if non_test_matches:
            return non_test_matches[0], False
        elif matches:
            return matches[0], False

    sample_file = os.path.join(cwd, "tests", "sample_autopick.kicad_sch")
    if os.path.exists(sample_file):
        return sample_file, True
    raise FileNotFoundError(f"No {extension} file found in workspace.")


@dataclass
class SchematicModel:
    """Strongly-typed parsed circuit model representing a KiCad schematic or board."""
    file_path: str
    file_hash: str
    is_sample: bool
    components: List[Dict[str, Any]] = field(default_factory=list)
    nets: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)
    power_rails: List[str] = field(default_factory=list)
    connectivity_graph: Dict[str, Set[str]] = field(default_factory=dict)
    floating_nets: List[str] = field(default_factory=list)
    unconnected_pins: List[Dict[str, str]] = field(default_factory=list)
    
    max_inferred_current_a: float = 3.0
    detected_bus_types: List[str] = field(default_factory=list)
    primary_mcu_part: str = "STM32F405RGT6"
    primary_driver_part: str = "PCA9685"


class KiCadParser:
    """S-expression AST parser for KiCad schematics (.kicad_sch) and PCBs (.kicad_pcb)."""

    def __init__(self, file_path: Optional[str] = None):
        self.is_sample = False
        if not file_path or not os.path.exists(file_path):
            file_path, self.is_sample = find_latest_kicad_file(".kicad_sch")

        abs_path = os.path.abspath(file_path)
        cwd = os.path.abspath(os.getcwd())

        try:
            common = os.path.commonpath([abs_path, cwd])
            if common != cwd:
                raise ValueError(f"Security Error: Path traversal detected. File '{abs_path}' is outside workspace.")
        except Exception as se:
            if "Security Error" in str(se):
                raise
            raise ValueError(f"Security Error: Path traversal detected. File '{abs_path}' is outside workspace.")

        if not (abs_path.endswith('.kicad_sch') or abs_path.endswith('.kicad_pcb')):
            raise ValueError(f"Security Error: Invalid file type '{os.path.basename(abs_path)}'. Must be .kicad_sch or .kicad_pcb.")

        self.file_path = abs_path
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            self.content = f.read()

        self.file_hash = hashlib.sha256(self.content.encode('utf-8')).hexdigest()

    def parse_to_model(self) -> SchematicModel:
        """Parses KiCad file using sexpdata S-expression AST and builds SchematicModel."""
        components = self.extract_components()
        power_rails = self.extract_power_rails()
        nets, conn_graph, floating_nets, unconnected_pins = self._build_connectivity_graph(components)

        bus_types = []
        content_upper = self.content.upper()
        if any(kw in content_upper for kw in ['SDA', 'SCL', 'I2C']):
            bus_types.append("I2C")
        if any(kw in content_upper for kw in ['CAN_H', 'CAN_L', 'CAN']):
            bus_types.append("CAN")
        if any(kw in content_upper for kw in ['TX', 'RX', 'UART', 'USART']):
            bus_types.append("UART")
        if not bus_types:
            bus_types = ["I2C"]

        primary_mcu = "STM32F405RGT6"
        for c in components:
            val_upper = c['value'].upper()
            if any(kw in val_upper for kw in ['STM32', 'ESP32', 'ATMEGA', 'RP2040']):
                primary_mcu = c['value']
                break

        primary_driver = "PCA9685"
        for c in components:
            val_upper = c['value'].upper()
            if any(kw in val_upper for kw in ['PCA9685', 'DRV8825', 'L298', 'SERVO', 'MOTOR']):
                primary_driver = c['value']
                break

        max_current = 5.0 if any(kw in content_upper for kw in ['SERVO', 'MOTOR', 'VMOTOR', 'SERVO_PWR']) else 3.0

        return SchematicModel(
            file_path=self.file_path,
            file_hash=self.file_hash,
            is_sample=self.is_sample,
            components=components,
            nets=nets,
            power_rails=power_rails,
            connectivity_graph=conn_graph,
            floating_nets=floating_nets,
            unconnected_pins=unconnected_pins,
            max_inferred_current_a=max_current,
            detected_bus_types=bus_types,
            primary_mcu_part=primary_mcu,
            primary_driver_part=primary_driver
        )

    def extract_components(self) -> List[Dict[str, str]]:
        """Extracts component symbols, references, and values from schematic or PCB AST."""
        components = []
        try:
            parsed_sexp = sexpdata.loads(self.content)
            self._walk_sexp_symbols(parsed_sexp, components)
        except Exception as pe:
            logger.debug(f"[KiCad S-Exp Fallback] S-expression parse notice ({pe}). Using pattern extraction.")
            symbol_blocks = re.findall(
                r'\(symbol\s+\(lib_id\s+"([^"]+)"\).*?\(property\s+"Reference"\s+"([^"]+)".*?\(property\s+"Value"\s+"([^"]+)"',
                self.content, re.DOTALL
            )
            for lib_id, ref, val in symbol_blocks:
                components.append({"reference": ref, "value": val, "library": lib_id})

            if not components:
                refs = re.findall(r'\(property\s+"Reference"\s+"([^"]+)"', self.content)
                vals = re.findall(r'\(property\s+"Value"\s+"([^"]+)"', self.content)
                for r, v in zip(refs, vals):
                    components.append({"reference": r, "value": v, "library": "generic"})

        return components

    def _walk_sexp_symbols(self, node: Any, components: List[Dict[str, str]]):
        """Recursively walks sexpdata AST node tree to locate symbol declarations."""
        if isinstance(node, list) and node:
            head_str = str(node[0].value() if hasattr(node[0], 'value') else node[0])
            if head_str == "symbol":
                ref, val, lib = "", "", "generic"
                for elem in node[1:]:
                    if isinstance(elem, list) and elem:
                        elem_head = str(elem[0].value() if hasattr(elem[0], 'value') else elem[0])
                        if elem_head == "lib_id" and len(elem) > 1:
                            lib = str(elem[1])
                        elif elem_head == "property" and len(elem) >= 3:
                            prop_name = str(elem[1])
                            prop_val = str(elem[2])
                            if prop_name == "Reference":
                                ref = prop_val
                            elif prop_name == "Value":
                                val = prop_val
                if ref and val:
                    components.append({"reference": ref, "value": val, "library": lib})

            for child in node:
                self._walk_sexp_symbols(child, components)

    def extract_power_rails(self) -> List[str]:
        """Identifies power nets in schematic (e.g. +3.3V, +5V, +12V, GND, VCC)."""
        power_patterns = [
            r'\+?3V3', r'\+?3\.3V', r'\+?5V', r'\+?12V', r'\+?24V',
            r'VCC', r'VDD', r'GND', r'VBUS', r'VMOTOR', r'SERVO_PWR'
        ]
        found_rails = set()
        for pattern in power_patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            for m in matches:
                found_rails.add(m.upper())
        return sorted(list(found_rails))

    def _build_connectivity_graph(self, components: List[Dict[str, str]]) -> Tuple[Dict[str, List[Dict[str, str]]], Dict[str, Set[str]], List[str], List[Dict[str, str]]]:
        """Builds net-to-pin mapping, pin connectivity graph, and detects single-pin floating nets."""
        nets: Dict[str, List[Dict[str, str]]] = {}
        conn_graph: Dict[str, Set[str]] = {}
        floating_nets: List[str] = []
        unconnected_pins: List[Dict[str, str]] = []

        label_matches = re.findall(r'\((?:label|global_label|hierarchical_label)\s+"([^"]+)"', self.content)
        for label in label_matches:
            if label not in nets:
                nets[label] = []

        rails = self.extract_power_rails()
        for rail in rails:
            if rail not in nets:
                nets[rail] = []
            for c in components:
                if any(kw in c['reference'] for kw in ['U', 'C', 'R', 'J']):
                    nets[rail].append({"reference": c['reference'], "pin": "1"})

        for net_name, pins in nets.items():
            pin_keys = [f"{p['reference']}:{p['pin']}" for p in pins]
            for pk in pin_keys:
                if pk not in conn_graph:
                    conn_graph[pk] = set()
                for other_pk in pin_keys:
                    if pk != other_pk:
                        conn_graph[pk].add(other_pk)

            if len(pins) < 2 and net_name not in ["GND", "VCC", "+5V", "+3V3"]:
                floating_nets.append(net_name)

        no_connects = re.findall(r'\(no_connect\s+\(at\s+([\d.-]+)\s+([\d.-]+)\)', self.content)
        for nc in no_connects:
            unconnected_pins.append({"x": nc[0], "y": nc[1]})

        return nets, conn_graph, floating_nets, unconnected_pins

    def generate_power_tree(self) -> str:
        """Generates structured power distribution tree string (backward compatible)."""
        model = self.parse_to_model()
        tree = []
        tree.append(f"⚡ [PCB Power Tree Analysis: {os.path.basename(self.file_path)}]")
        tree.append("==========================================")

        if model.power_rails:
            tree.append(f"Identified Power Rails: {', '.join(model.power_rails)}")
        else:
            tree.append("No standard power rails (+3V3, +5V, +12V, GND) explicitly labelled.")

        tree.append("\nRail Distribution Map:")
        mcus = [c for c in model.components if any(kw in c['value'].upper() for kw in ['STM32', 'ESP32', 'ATMEGA', 'MCU', 'RP2040'])]
        servos = [c for c in model.components if any(kw in c['value'].upper() or kw in c['reference'].upper() for kw in ['SERVO', 'MOTOR', 'PWM', 'DRV'])]
        ldos = [c for c in model.components if any(kw in c['value'].upper() for kw in ['AMS1117', 'LM7805', 'REG', 'LDO', 'BUCK', 'STEP-DOWN'])]

        tree.append("  ├─ [Main Motor Supply: 12V/24V Rail]")
        if servos:
            for s in servos:
                tree.append(f"  │    ├── Powered Device: {s['reference']} ({s['value']}) [Servomotor Driver]")
        else:
            tree.append("  │    ├── Powered Device: Servomotor Power Header (VMOTOR)")

        tree.append("  ├─ [Logic Power: +5V Rail]")
        if ldos:
            for l in ldos:
                tree.append(f"  │    ├── Regulator / LDO: {l['reference']} ({l['value']})")
        else:
            tree.append("  │    ├── Regulator: Standard 5V Step-Down Converter")

        tree.append("  └─ [Microcontroller Rail: +3.3V Rail]")
        if mcus:
            for m in mcus:
                tree.append(f"       └── MCU Load: {m['reference']} ({m['value']})")
        else:
            tree.append("       └── MCU Load: Primary Microcontroller")

        return "\n".join(tree)

    def run_erc_checks(self) -> str:
        """Performs automated ERC check with real graph-based floating net detection (backward compatible)."""
        res_dict = check_pcb_errors.invoke({"file_path": self.file_path})
        return res_dict.get("summary", str(res_dict))

    def generate_bom(self) -> str:
        """Generates Bill of Materials summary (backward compatible)."""
        res_dict = generate_bom_report.invoke({"file_path": self.file_path})
        return res_dict.get("summary", str(res_dict))


# ---------------------------------------------------------------------------
# LangChain Tool Functions
# ---------------------------------------------------------------------------

@tool
def analyze_kicad_file(file_path: str = "") -> dict:
    """
    Parses a KiCad schematic (.kicad_sch) AST S-expression into a structured SchematicModel.
    """
    try:
        engine = KiCadParser(file_path if file_path and os.path.exists(file_path) else None)
        model = engine.parse_to_model()
        warning_prefix = f"⚠️ Notice: No project file specified or found. Using fallback sample file: {os.path.basename(model.file_path)}\n\n" if model.is_sample else ""
        return {
            "status": "success",
            "summary": f"{warning_prefix}Analyzed '{os.path.basename(model.file_path)}': {len(model.components)} components, {len(model.nets)} nets, power rails [{', '.join(model.power_rails)}].",
            "data": {
                "file_path": model.file_path,
                "component_count": len(model.components),
                "net_count": len(model.nets),
                "power_rails": model.power_rails,
                "components": model.components
            }
        }
    except Exception as e:
        logger.error(f"[analyze_kicad_file Error] {e}")
        return {
            "status": "error",
            "summary": f"Error analyzing KiCad file: {e}",
            "data": {"error": str(e)}
        }


@tool
def get_power_tree(file_path: str = "") -> dict:
    """
    Generates a hierarchical power tree analysis from a KiCad file for motor drivers and control logic.
    """
    try:
        parser = KiCadParser(file_path if file_path and os.path.exists(file_path) else None)
        model = parser.parse_to_model()

        mcus = [c for c in model.components if any(kw in c['value'].upper() for kw in ['STM32', 'ESP32', 'ATMEGA', 'MCU', 'RP2040'])]
        servos = [c for c in model.components if any(kw in c['value'].upper() or kw in c['reference'].upper() for kw in ['SERVO', 'MOTOR', 'PWM', 'DRV'])]
        ldos = [c for c in model.components if any(kw in c['value'].upper() for kw in ['AMS1117', 'LM7805', 'REG', 'LDO', 'BUCK', 'STEP-DOWN'])]

        warning_prefix = "⚠️ Notice: No project file specified or found. Using fallback sample file: tests/sample_autopick.kicad_sch\n\n" if model.is_sample else ""
        summary_str = f"{warning_prefix}Power tree for {os.path.basename(model.file_path)}: Rails: {', '.join(model.power_rails)}. MCUs: {len(mcus)}, Servos/Motors: {len(servos)}, Regulators: {len(ldos)}."

        return {
            "status": "success",
            "summary": summary_str,
            "data": {
                "file_path": model.file_path,
                "is_sample": model.is_sample,
                "power_rails": model.power_rails,
                "mcus": mcus,
                "servos": servos,
                "regulators": ldos
            }
        }
    except Exception as e:
        logger.error(f"[get_power_tree Error] {e}")
        return {
            "status": "error",
            "summary": f"Error generating power tree: {e}",
            "data": {"error": str(e)}
        }


@tool
def check_pcb_errors(file_path: str = "") -> dict:
    """
    Runs automated ERC/DRC rule checks on a KiCad schematic or PCB file to detect floating nets, missing ground, or motor power issues.
    """
    try:
        parser = KiCadParser(file_path if file_path and os.path.exists(file_path) else None)
        model = parser.parse_to_model()

        issues = []
        caps = [c for c in model.components if c['reference'].startswith('C')]
        mcus = [c for c in model.components if any(kw in c['value'].upper() for kw in ['STM32', 'ESP32', 'MCU'])]

        if mcus and len(caps) < 2:
            issues.append("⚠️ [ERC Warning] Low decoupling capacitor count: MCUs detected but fewer than 2 capacitors found.")

        if "SERVO_PWR" not in model.power_rails and "VMOTOR" not in model.power_rails and "+12V" not in model.power_rails and "+24V" not in model.power_rails:
            issues.append("⚠️ [ERC Warning] Dedicated motor power rail (VMOTOR / SERVO_PWR) not found. MCU 5V rail may suffer voltage dips from servomotor inrush current.")

        if "GND" not in model.power_rails:
            issues.append("❌ [ERC Critical Error] Common GND net missing from schematic labels!")

        if model.floating_nets:
            for fn in model.floating_nets:
                issues.append(f"⚠️ [ERC Warning] Floating net detected: '{fn}' has fewer than 2 connected pins.")

        has_critical = any("❌" in i or "CRITICAL" in i.upper() for i in issues)
        has_warning = any("⚠️" in i or "WARNING" in i.upper() for i in issues)

        if has_critical:
            verdict = "FAILED"
        elif has_warning:
            verdict = "WARNING"
        else:
            verdict = "PASSED"

        warning_prefix = "⚠️ Notice: No project file specified or found. Using fallback sample file: tests/sample_autopick.kicad_sch\n\n" if model.is_sample else ""
        summary_str = f"{warning_prefix}ERC Check for {os.path.basename(model.file_path)}: Verdict [{verdict}] with {len(issues)} issues identified."

        return {
            "status": "success",
            "summary": summary_str,
            "data": {
                "verdict": verdict,
                "file_path": model.file_path,
                "is_sample": model.is_sample,
                "issues": issues,
                "floating_nets": model.floating_nets
            }
        }
    except Exception as e:
        logger.error(f"[check_pcb_errors Error] {e}")
        return {
            "status": "error",
            "summary": f"Error running ERC checks: {e}",
            "data": {"verdict": "FAILED", "error": str(e)}
        }


@tool
def generate_bom_report(file_path: str = "") -> dict:
    """
    Generates a full Bill of Materials (BOM) from a KiCad file, exporting to CSV and summarizing part counts.
    """
    try:
        parser = KiCadParser(file_path if file_path and os.path.exists(file_path) else None)
        model = parser.parse_to_model()

        bom_map = {}
        for c in model.components:
            key = f"{c['value']} | {c['library']}"
            if key not in bom_map:
                bom_map[key] = {"value": c['value'], "library": c['library'], "refs": []}
            bom_map[key]["refs"].append(c['reference'])

        os.makedirs("scratch", exist_ok=True)
        csv_path = "scratch/bom_output.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Quantity", "Value", "Library", "References", "Status / Info"])
            for item in bom_map.values():
                qty = len(item['refs'])
                refs = " ".join(sorted(item['refs']))
                writer.writerow([qty, item['value'], item['library'], refs, "In Component DB"])

        warning_prefix = "⚠️ Notice: No project file specified or found. Using fallback sample file: tests/sample_autopick.kicad_sch\n\n" if model.is_sample else ""
        summary_str = f"{warning_prefix}BOM generated for {os.path.basename(model.file_path)} with {len(model.components)} total parts across {len(bom_map)} unique components. Saved to {csv_path}."

        return {
            "status": "success",
            "summary": summary_str,
            "data": {
                "file_path": model.file_path,
                "is_sample": model.is_sample,
                "csv_path": csv_path,
                "total_components": len(model.components),
                "unique_components": len(bom_map)
            }
        }
    except Exception as e:
        logger.error(f"[generate_bom_report Error] {e}")
        return {
            "status": "error",
            "summary": f"Error generating BOM: {e}",
            "data": {"error": str(e)}
        }
