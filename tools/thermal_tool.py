"""
PCB Thermal Loss & Current Density Calculator Tool for Jarvis Copilot.
Implements IPC-2221 trace width math, I^2R copper power loss, and linear regulator junction thermal dissipation.
"""

import math
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

@tool
def calculate_thermal_loss(
    current_amps: float = 3.0,
    trace_width_mils: float = 30.0,
    trace_length_mm: float = 50.0,
    copper_oz: float = 1.0,
    vin_v: float = 12.0,
    vout_v: float = 5.0,
    reg_current_a: float = 0.5
) -> str:
    """
    Calculates IPC-2221 copper trace temperature rise, I^2R power loss, and regulator junction thermal rise.
    
    Args:
        current_amps: Peak current flowing through trace (e.g. 3.0A for servomotors).
        trace_width_mils: Trace width in mils (1 mil = 0.001 inch).
        trace_length_mm: Trace length in millimeters.
        copper_oz: Copper weight in ounces (1.0 oz = 1.37 mil thickness).
        vin_v: Input voltage to linear regulator (e.g. 12V).
        vout_v: Output voltage from linear regulator (e.g. 5V).
        reg_current_a: Current drawn through linear regulator (e.g. 0.5A).
    """
    # 1. Copper Trace Resistance & I^2R Power Loss
    copper_thickness_mils = copper_oz * 1.37
    cross_section_sq_mils = trace_width_mils * copper_thickness_mils
    
    # Resistivity of copper = 1.724e-8 ohm-m (0.6788 uOhm-inch)
    length_inches = trace_length_mm / 25.4
    resistance_ohms = (0.6788e-6 * length_inches) / (cross_section_sq_mils * 1e-6)
    power_loss_watts = (current_amps ** 2) * resistance_ohms

    # IPC-2221 Temperature Rise Estimation: I = k * (dT^0.44) * (A^0.725)
    # k = 0.048 for external layers
    if cross_section_sq_mils > 0:
        dt_celsius = (current_amps / (0.048 * (cross_section_sq_mils ** 0.725))) ** (1 / 0.44)
    else:
        dt_celsius = 999.0

    # Minimum recommended width for 10°C rise according to IPC-2221
    req_area_sq_mils = (current_amps / (0.048 * (10.0 ** 0.44))) ** (1 / 0.725)
    req_width_mils = req_area_sq_mils / copper_thickness_mils

    # 2. Linear Regulator (AMS1117 / LM7805) Thermal Dissipation
    v_drop = max(0.0, vin_v - vout_v)
    reg_power_watts = v_drop * reg_current_a
    # Typical SOT-223 Rth_JA = 90 °C/W on 1oz copper
    r_th_ja = 90.0
    ambient_temp = 25.0
    junction_temp = ambient_temp + (reg_power_watts * r_th_ja)

    # 3. Formulate IPC Thermal Report Summary
    report = [
        "============================================================",
        "          AUTOPICK PCB THERMAL & IPC-2221 REPORT",
        "============================================================",
        f"Trace Width: {trace_width_mils:.1f} mils ({trace_width_mils*0.0254:.2f} mm) | Length: {trace_length_mm:.1f} mm | Copper: {copper_oz:.1f} oz",
        f"Peak Trace Current: {current_amps:.2f} A",
        f"Estimated Resistance: {resistance_ohms*1000:.2f} mOhm",
        f"Copper I^2R Power Loss: {power_loss_watts*1000:.2f} mW",
        f"Estimated Trace Temp Rise: +{dt_celsius:.1f} °C (Ambient +25°C -> {dt_celsius+25:.1f}°C)",
        f"IPC-2221 Recommended Min Width (10°C rise): {req_width_mils:.1f} mils ({req_width_mils*0.0254:.2f} mm)",
        "------------------------------------------------------------",
        f"Linear Regulator Drop: {vin_v:.1f}V -> {vout_v:.1f}V ({v_drop:.1f}V Drop at {reg_current_a:.2f}A)",
        f"Regulator Power Dissipation: {reg_power_watts:.2f} W",
        f"SOT-223 Junction Temp: {junction_temp:.1f} °C (Max Limit: 125°C)",
        "============================================================"
    ]

    # Evaluation Alerts
    if dt_celsius > 30.0:
        report.append("⚠️ WARNING: High trace temperature rise! Increase trace width or copper weight to 2oz.")
    elif trace_width_mils < req_width_mils:
        report.append("💡 RECOMMENDATION: Trace width is below IPC-2221 10°C target. Consider widening rail.")
    else:
        report.append("✅ PASS: Trace thermal loss and current density are within safe IPC-2221 margins.")

    if junction_temp > 125.0:
        report.append("🚨 DANGER: Regulator junction exceeds 125°C thermal limit! Add copper thermal via pad or buck converter.")
    elif junction_temp > 85.0:
        report.append("⚠️ NOTICE: Regulator runs warm (>85°C). Ensure thermal copper pour connected to GND tab.")

    return "\n".join(report)
