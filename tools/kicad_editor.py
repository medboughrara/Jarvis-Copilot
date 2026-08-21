"""
🛠️ Programmatic KiCad Schematic (.kicad_sch) and PCB (.kicad_pcb) AST Editor.

Provides standalone, high-fidelity S-expression AST reading, mutation, component placement,
net wiring, and serializing for KiCad projects without requiring external GUI IPC.
"""

import os
import re
import uuid
import sexpdata
from typing import Dict, List, Any, Optional, Tuple
import config

logger = config.get_logger(__name__)


def generate_kicad_uuid() -> str:
    """Generates a standard KiCad-formatted UUID string."""
    return str(uuid.uuid4())


class KiCadSchematicEditor:
    """Programmatic editor for KiCad v6/v7/v8/v9 schematic files (.kicad_sch)."""

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path
        self.raw_ast = None
        self.version = "20231120"
        self.generator = "jarvis_pcb_copilot"
        self.uuid = generate_kicad_uuid()
        self.components = []
        self.wires = []
        self.labels = []
        
        if file_path and os.path.exists(file_path):
            self.load(file_path)
        else:
            self._init_empty_schematic()

    def _init_empty_schematic(self):
        """Initializes a new blank KiCad schematic structure."""
        self.raw_ast = [
            sexpdata.Symbol("kicad_sch"),
            [sexpdata.Symbol("version"), 20231120],
            [sexpdata.Symbol("generator"), "jarvis_pcb_copilot"],
            [sexpdata.Symbol("uuid"), self.uuid],
            [sexpdata.Symbol("paper"), "A4"]
        ]

    def load(self, file_path: str):
        """Loads and parses an existing .kicad_sch file."""
        self.file_path = file_path
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.raw_ast = sexpdata.loads(content)
        self._parse_internal()

    def _parse_internal(self):
        """Extracts high-level components and labels from loaded AST."""
        self.components = []
        self.wires = []
        self.labels = []
        
        if not isinstance(self.raw_ast, list):
            return

        for item in self.raw_ast:
            if isinstance(item, list) and len(item) > 0:
                tag = str(item[0])
                if tag in ["symbol", "Symbol"]:
                    comp = self._extract_symbol_info(item)
                    if comp:
                        self.components.append(comp)
                elif tag in ["wire", "Wire"]:
                    self.wires.append(item)
                elif tag in ["label", "Label", "global_label"]:
                    self.labels.append(item)

    def _extract_symbol_info(self, symbol_node: list) -> Dict[str, Any]:
        """Extracts reference, value, footprint, and position from a symbol node."""
        info = {
            "lib_id": "",
            "reference": "",
            "value": "",
            "footprint": "",
            "at": (0.0, 0.0, 0.0),
            "uuid": "",
            "node": symbol_node
        }
        for sub in symbol_node:
            if isinstance(sub, list) and len(sub) > 0:
                sub_tag = str(sub[0])
                if sub_tag in ["lib_id", "lib_name"] and len(sub) > 1:
                    info["lib_id"] = str(sub[1])
                elif sub_tag in ["at", "At"] and len(sub) >= 3:
                    info["at"] = (float(sub[1]), float(sub[2]), float(sub[3]) if len(sub) > 3 else 0.0)
                elif sub_tag in ["uuid", "Uuid"] and len(sub) > 1:
                    info["uuid"] = str(sub[1])
                elif sub_tag in ["property", "Property"] and len(sub) >= 3:
                    prop_name = str(sub[1])
                    prop_val = str(sub[2])
                    if prop_name == "Reference":
                        info["reference"] = prop_val
                    elif prop_name == "Value":
                        info["value"] = prop_val
                    elif prop_name == "Footprint":
                        info["footprint"] = prop_val
        return info

    def add_symbol(
        self,
        reference: str,
        value: str,
        footprint: str = "",
        at: Tuple[float, float] = (100.0, 100.0),
        lib_id: str = "Device:R"
    ) -> Dict[str, Any]:
        """
        Adds a new component symbol to the schematic AST.
        """
        comp_uuid = generate_kicad_uuid()
        x, y = at
        
        symbol_node = [
            sexpdata.Symbol("symbol"),
            [sexpdata.Symbol("lib_id"), lib_id],
            [sexpdata.Symbol("at"), float(x), float(y), 0],
            [sexpdata.Symbol("unit"), 1],
            [sexpdata.Symbol("in_bom"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("on_board"), sexpdata.Symbol("yes")],
            [sexpdata.Symbol("uuid"), comp_uuid],
            [
                sexpdata.Symbol("property"),
                "Reference",
                reference,
                [sexpdata.Symbol("at"), float(x), float(y) - 2.5, 0],
                [sexpdata.Symbol("effects"), [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]]]
            ],
            [
                sexpdata.Symbol("property"),
                "Value",
                value,
                [sexpdata.Symbol("at"), float(x), float(y) + 2.5, 0],
                [sexpdata.Symbol("effects"), [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]]]
            ],
            [
                sexpdata.Symbol("property"),
                "Footprint",
                footprint or "Resistor_SMD:R_0805_2012Metric",
                [sexpdata.Symbol("at"), float(x), float(y), 0],
                [sexpdata.Symbol("effects"), [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]], [sexpdata.Symbol("hide"), sexpdata.Symbol("yes")]]
            ]
        ]

        self.raw_ast.append(symbol_node)
        
        comp_record = {
            "reference": reference,
            "value": value,
            "footprint": footprint,
            "lib_id": lib_id,
            "at": (x, y, 0.0),
            "uuid": comp_uuid,
            "node": symbol_node
        }
        self.components.append(comp_record)
        logger.info(f"[KiCadSchematicEditor] Added symbol {reference} ({value}) at ({x}, {y})")
        return comp_record

    def add_wire(self, start: Tuple[float, float], end: Tuple[float, float]) -> list:
        """Adds a connecting wire segment between two coordinates."""
        x1, y1 = start
        x2, y2 = end
        wire_uuid = generate_kicad_uuid()
        
        wire_node = [
            sexpdata.Symbol("wire"),
            [
                sexpdata.Symbol("pts"),
                [sexpdata.Symbol("xy"), float(x1), float(y1)],
                [sexpdata.Symbol("xy"), float(x2), float(y2)]
            ],
            [sexpdata.Symbol("stroke"), [sexpdata.Symbol("width"), 0], [sexpdata.Symbol("type"), sexpdata.Symbol("default")]],
            [sexpdata.Symbol("uuid"), wire_uuid]
        ]
        self.raw_ast.append(wire_node)
        self.wires.append(wire_node)
        return wire_node

    def add_label(self, name: str, at: Tuple[float, float], orientation: int = 0) -> list:
        """Adds a net label to the schematic at (x, y)."""
        x, y = at
        label_uuid = generate_kicad_uuid()
        
        label_node = [
            sexpdata.Symbol("label"),
            name,
            [sexpdata.Symbol("at"), float(x), float(y), int(orientation)],
            [sexpdata.Symbol("effects"), [sexpdata.Symbol("font"), [sexpdata.Symbol("size"), 1.27, 1.27]]],
            [sexpdata.Symbol("uuid"), label_uuid]
        ]
        self.raw_ast.append(label_node)
        self.labels.append(label_node)
        logger.info(f"[KiCadSchematicEditor] Added net label '{name}' at ({x}, {y})")
        return label_node

    def connect_component_to_net(
        self,
        reference: str,
        pin_offset_xy: Tuple[float, float],
        net_name: str,
        wire_length: float = 5.0
    ):
        """
        Connects a component's pin location to a named net via an attached wire and net label.
        """
        target = next((c for c in self.components if c["reference"] == reference), None)
        if not target:
            raise ValueError(f"Component '{reference}' not found in schematic.")

        comp_x, comp_y, _ = target["at"]
        pin_x = comp_x + pin_offset_xy[0]
        pin_y = comp_y + pin_offset_xy[1]
        
        label_x = pin_x + wire_length
        label_y = pin_y
        
        # 1. Wire from pin to label
        self.add_wire((pin_x, pin_y), (label_x, label_y))
        # 2. Add Net Label
        self.add_label(net_name, (label_x, label_y))
        logger.info(f"[KiCadSchematicEditor] Connected {reference} pin to net '{net_name}'")

    def save(self, file_path: Optional[str] = None) -> str:
        """Serializes and saves the modified S-expression AST to file."""
        target_path = file_path or self.file_path
        if not target_path:
            raise ValueError("No file path specified for saving schematic.")
        
        parent_dir = os.path.dirname(os.path.abspath(target_path))
        os.makedirs(parent_dir, exist_ok=True)
        
        serialized = sexpdata.dumps(self.raw_ast)
        # Format s-expression nicely for KiCad readability
        serialized_formatted = serialized.replace(" (", "\n  (")
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(serialized_formatted + "\n")
            
        self.file_path = target_path
        logger.info(f"[KiCadSchematicEditor] Saved schematic to '{target_path}'")
        return target_path


class KiCadPcbEditor:
    """Programmatic editor for KiCad PCB board files (.kicad_pcb)."""

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path
        self.raw_ast = None
        self.uuid = generate_kicad_uuid()
        self.footprints = []
        self.tracks = []
        self.nets = {}
        
        if file_path and os.path.exists(file_path):
            self.load(file_path)
        else:
            self._init_empty_pcb()

    def _init_empty_pcb(self):
        """Initializes a new blank KiCad PCB board AST."""
        self.raw_ast = [
            sexpdata.Symbol("kicad_pcb"),
            [sexpdata.Symbol("version"), 20231120],
            [sexpdata.Symbol("generator"), "jarvis_pcb_copilot"],
            [sexpdata.Symbol("generator_version"), "9.0"],
            [sexpdata.Symbol("general"), [sexpdata.Symbol("thickness"), 1.6]],
            [sexpdata.Symbol("paper"), "A4"],
            [sexpdata.Symbol("layers"), [0, "F.Cu", "signal"], [31, "B.Cu", "signal"], [36, "F.SilkS", "user"], [37, "B.SilkS", "user"], [38, "Edge.Cuts", "user"]],
            [sexpdata.Symbol("net"), 0, ""]
        ]

    def load(self, file_path: str):
        """Loads and parses an existing .kicad_pcb file."""
        self.file_path = file_path
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.raw_ast = sexpdata.loads(content)
        self._parse_internal()

    def _parse_internal(self):
        """Extracts footprints, tracks, and nets from loaded PCB AST."""
        self.footprints = []
        self.tracks = []
        self.nets = {}
        
        if not isinstance(self.raw_ast, list):
            return

        for item in self.raw_ast:
            if isinstance(item, list) and len(item) > 0:
                tag = str(item[0])
                if tag in ["footprint", "Footprint", "module"]:
                    self.footprints.append(item)
                elif tag in ["segment", "Segment"]:
                    self.tracks.append(item)
                elif tag in ["net", "Net"] and len(item) >= 3:
                    net_id = int(item[1])
                    net_name = str(item[2])
                    self.nets[net_name] = net_id

    def add_net(self, net_name: str) -> int:
        """Registers a named net in the PCB netlist."""
        if net_name in self.nets:
            return self.nets[net_name]
        
        new_id = len(self.nets)
        net_node = [sexpdata.Symbol("net"), new_id, net_name]
        self.raw_ast.append(net_node)
        self.nets[net_name] = new_id
        return new_id

    def add_footprint(
        self,
        reference: str,
        value: str,
        footprint_name: str = "Resistor_SMD:R_0805_2012Metric",
        at: Tuple[float, float] = (100.0, 100.0),
        layer: str = "F.Cu"
    ) -> list:
        """Adds a component footprint to the PCB layout."""
        x, y = at
        fp_uuid = generate_kicad_uuid()
        
        fp_node = [
            sexpdata.Symbol("footprint"),
            footprint_name,
            [sexpdata.Symbol("layer"), layer],
            [sexpdata.Symbol("uuid"), fp_uuid],
            [sexpdata.Symbol("at"), float(x), float(y)],
            [sexpdata.Symbol("property"), "Reference", reference, [sexpdata.Symbol("at"), float(x), float(y) - 2.0], [sexpdata.Symbol("layer"), "F.SilkS"]],
            [sexpdata.Symbol("property"), "Value", value, [sexpdata.Symbol("at"), float(x), float(y) + 2.0], [sexpdata.Symbol("layer"), "F.Fab"]],
            [
                sexpdata.Symbol("pad"),
                "1",
                sexpdata.Symbol("smd"),
                sexpdata.Symbol("roundrect"),
                [sexpdata.Symbol("at"), -1.0, 0.0],
                [sexpdata.Symbol("size"), 1.0, 1.3],
                [sexpdata.Symbol("layers"), "F.Cu", "F.Paste", "F.Mask"],
                [sexpdata.Symbol("uuid"), generate_kicad_uuid()]
            ],
            [
                sexpdata.Symbol("pad"),
                "2",
                sexpdata.Symbol("smd"),
                sexpdata.Symbol("roundrect"),
                [sexpdata.Symbol("at"), 1.0, 0.0],
                [sexpdata.Symbol("size"), 1.0, 1.3],
                [sexpdata.Symbol("layers"), "F.Cu", "F.Paste", "F.Mask"],
                [sexpdata.Symbol("uuid"), generate_kicad_uuid()]
            ]
        ]
        
        self.raw_ast.append(fp_node)
        self.footprints.append(fp_node)
        logger.info(f"[KiCadPcbEditor] Added footprint {reference} ({value}) at ({x}, {y})")
        return fp_node

    def add_track(
        self,
        net_name: str,
        start: Tuple[float, float],
        end: Tuple[float, float],
        width_mm: float = 0.25,
        layer: str = "F.Cu"
    ) -> list:
        """Adds a routed copper track segment between two coordinates."""
        net_id = self.add_net(net_name)
        x1, y1 = start
        x2, y2 = end
        track_uuid = generate_kicad_uuid()
        
        track_node = [
            sexpdata.Symbol("segment"),
            [sexpdata.Symbol("start"), float(x1), float(y1)],
            [sexpdata.Symbol("end"), float(x2), float(y2)],
            [sexpdata.Symbol("width"), float(width_mm)],
            [sexpdata.Symbol("layer"), layer],
            [sexpdata.Symbol("net"), int(net_id)],
            [sexpdata.Symbol("uuid"), track_uuid]
        ]
        self.raw_ast.append(track_node)
        self.tracks.append(track_node)
        logger.info(f"[KiCadPcbEditor] Added copper track for net '{net_name}' from {start} to {end}")
        return track_node

    def save(self, file_path: Optional[str] = None) -> str:
        """Serializes and saves the modified PCB layout AST to file."""
        target_path = file_path or self.file_path
        if not target_path:
            raise ValueError("No file path specified for saving PCB.")
        
        parent_dir = os.path.dirname(os.path.abspath(target_path))
        os.makedirs(parent_dir, exist_ok=True)
        
        serialized = sexpdata.dumps(self.raw_ast)
        serialized_formatted = serialized.replace(" (", "\n  (")
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(serialized_formatted + "\n")
            
        self.file_path = target_path
        logger.info(f"[KiCadPcbEditor] Saved PCB to '{target_path}'")
        return target_path
