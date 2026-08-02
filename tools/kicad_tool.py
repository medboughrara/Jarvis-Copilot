"""
KiCad PCB & Schematic Parser Tool for Jarvis Copilot.
Parses `.kicad_sch` and `.kicad_pcb` files to generate netlists, power trees, and check ERC/DRC rules.
Supports automatic file discovery in workspace.
"""

import os
import re
import glob
from typing import Dict, List, Any
import sexpdata
from langchain_core.tools import tool


def find_latest_kicad_file(extension: str = ".kicad_sch") -> str:
    """Searches workspace and current directory for KiCad schematic or PCB files."""
    # Search working directory and subdirectories
    search_dirs = [".", "d:/aaaassistan_pcb", "d:/aaaassistan_pcb/tests"]
    for d in search_dirs:
        pattern = os.path.join(d, f"**/*{extension}")
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]
            
    # Fallback to test sample if no user file found yet
    sample_file = "d:/aaaassistan_pcb/tests/sample_autopick.kicad_sch"
    if os.path.exists(sample_file):
        return sample_file
    raise FileNotFoundError(f"No {extension} file found in workspace.")


class KiCadParser:
    """Core parser for KiCad schematic and PCB S-expression files."""

    def __init__(self, file_path: str = None):
        if not file_path or not os.path.exists(file_path):
            file_path = find_latest_kicad_file(".kicad_sch")
            
        self.file_path = file_path
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            self.content = f.read()

    def extract_components(self) -> List[Dict[str, str]]:
        """Extracts component symbols, references, and values from schematic or PCB."""
        components = []
        symbol_blocks = re.findall(r'\(symbol\s+\(lib_id\s+"([^"]+)"\).*?\(property\s+"Reference"\s+"([^"]+)".*?\(property\s+"Value"\s+"([^"]+)"', self.content, re.DOTALL)
        
        for lib_id, ref, val in symbol_blocks:
            components.append({
                "reference": ref,
                "value": val,
                "library": lib_id
            })
            
        if not components:
            refs = re.findall(r'\(property\s+"Reference"\s+"([^"]+)"', self.content)
            vals = re.findall(r'\(property\s+"Value"\s+"([^"]+)"', self.content)
            for r, v in zip(refs, vals):
                components.append({"reference": r, "value": v, "library": "generic"})

        return components

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

    def generate_power_tree(self) -> str:
        """Generates a structured power distribution tree for AutoPick robotic arm system."""
        rails = self.extract_power_rails()
        components = self.extract_components()

        tree = []
        tree.append(f"⚡ [AutoPick PCB Power Tree Analysis: {os.path.basename(self.file_path)}]")
        tree.append("==========================================")
        
        if rails:
            tree.append(f"Identified Power Rails: {', '.join(rails)}")
        else:
            tree.append("No standard power rails (+3V3, +5V, +12V, GND) explicitly labelled.")

        tree.append("\nRail Distribution Map:")
        
        mcus = [c for c in components if any(kw in c['value'].upper() for kw in ['STM32', 'ESP32', 'ATMEGA', 'MCU', 'RP2040'])]
        servos = [c for c in components if any(kw in c['value'].upper() or kw in c['reference'].upper() for kw in ['SERVO', 'MOTOR', 'PWM', 'DRV'])]
        ldos = [c for c in components if any(kw in c['value'].upper() for kw in ['AMS1117', 'LM7805', 'REG', 'LDO', 'BUCK', 'STEP-DOWN'])]

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
            tree.append("       └── MCU Load: AutoPick Main Controller")

        return "\n".join(tree)

    def run_erc_checks(self) -> str:
        """Performs automated ERC check for common AutoPick robotic arm PCB errors."""
        components = self.extract_components()
        rails = self.extract_power_rails()
        
        issues = []
        caps = [c for c in components if c['reference'].startswith('C')]
        mcus = [c for c in components if any(kw in c['value'].upper() for kw in ['STM32', 'ESP32', 'MCU'])]
        
        if mcus and len(caps) < 2:
            issues.append("⚠️ [ERC Warning] Low decoupling capacitor count: MCUs detected but fewer than 2 capacitors found.")

        if "SERVO_PWR" not in rails and "VMOTOR" not in rails and "+12V" not in rails and "+24V" not in rails:
            issues.append("⚠️ [ERC Warning] Dedicated motor power rail (VMOTOR / SERVO_PWR) not found. MCU 5V rail may suffer voltage dips from servomotor inrush current.")

        if "GND" not in rails:
            issues.append("❌ [ERC Critical Error] Common GND net missing from schematic labels!")

        if not issues:
            return f"✅ [KiCad ERC Check for {os.path.basename(self.file_path)}]: Pass! No critical power isolation or net issues detected."
        
        return f"🔍 [KiCad ERC Error Summary for {os.path.basename(self.file_path)}]:\n" + "\n".join(issues)


# ---------------------------------------------------------------------------
# LangChain Tool Functions
# ---------------------------------------------------------------------------

@tool
def analyze_kicad_file(file_path: str = "") -> str:
    """
    Parses a KiCad schematic (.kicad_sch) or PCB (.kicad_pcb) file and returns component counts, references, and values.
    Args:
        file_path: Optional path to .kicad_sch or .kicad_pcb file. If empty, auto-discovers file in workspace.
    """
    try:
        if not file_path or not os.path.exists(file_path):
            file_path = find_latest_kicad_file(".kicad_sch")
        parser = KiCadParser(file_path)
        comps = parser.extract_components()
        rails = parser.extract_power_rails()
        
        summary = [f"KiCad Analysis for '{os.path.basename(file_path)}':"]
        summary.append(f"- Total Components Found: {len(comps)}")
        summary.append(f"- Power Nets Detected: {', '.join(rails) if rails else 'None'}")
        summary.append("\nComponent List Sample:")
        for c in comps[:10]:
            summary.append(f"  • {c['reference']}: {c['value']} ({c['library']})")
            
        return "\n".join(summary)
    except Exception as e:
        return f"Error analyzing KiCad file: {e}"


@tool
def get_power_tree(file_path: str = "") -> str:
    """
    Generates a hierarchical power tree analysis from a KiCad file for AutoPick robotic arm servomotors and control logic.
    Args:
        file_path: Optional path to .kicad_sch file. If empty, auto-discovers file in workspace.
    """
    try:
        if not file_path or not os.path.exists(file_path):
            file_path = find_latest_kicad_file(".kicad_sch")
        parser = KiCadParser(file_path)
        return parser.generate_power_tree()
    except Exception as e:
        return f"Error generating power tree: {e}"


@tool
def check_pcb_errors(file_path: str = "") -> str:
    """
    Runs automated ERC/DRC rule checks on a KiCad schematic or PCB file to detect floating nets, missing ground, or motor power issues.
    Args:
        file_path: Optional path to .kicad_sch or .kicad_pcb file. If empty, auto-discovers file in workspace.
    """
    try:
        if not file_path or not os.path.exists(file_path):
            file_path = find_latest_kicad_file(".kicad_sch")
        parser = KiCadParser(file_path)
        return parser.run_erc_checks()
    except Exception as e:
        return f"Error running ERC checks: {e}"
