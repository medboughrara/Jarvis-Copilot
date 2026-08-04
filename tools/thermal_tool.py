"""
PCB Thermal Loss & Current Density Calculator Tool for Jarvis Copilot.
Implements IPC-2221 trace width math, I^2R copper power loss, and linear regulator junction thermal dissipation.
Returns structured dictionaries adhering to the {status, data, summary} contract.
"""

import math
from typing import Dict, Any
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
) -> dict:
    """
    Calculates IPC-2221 copper trace temperature rise, I^2R power loss, and regulator junction thermal rise.
    """
    try:
        copper_thickness_mils = copper_oz * 1.37
        cross_section_sq_mils = trace_width_mils * copper_thickness_mils

        length_inches = trace_length_mm / 25.4
        resistance_ohms = (0.6788e-6 * length_inches) / (cross_section_sq_mils * 1e-6) if cross_section_sq_mils > 0 else 999.0
        power_loss_watts = (current_amps ** 2) * resistance_ohms

        if cross_section_sq_mils > 0:
            dt_celsius = (current_amps / (0.048 * (cross_section_sq_mils ** 0.725))) ** (1 / 0.44)
        else:
            dt_celsius = 999.0

        req_area_sq_mils = (current_amps / (0.048 * (10.0 ** 0.44))) ** (1 / 0.725)
        req_width_mils = req_area_sq_mils / copper_thickness_mils

        v_drop = max(0.0, vin_v - vout_v)
        reg_power_watts = v_drop * reg_current_a
        r_th_ja = 90.0
        ambient_temp = 25.0
        junction_temp = ambient_temp + (reg_power_watts * r_th_ja)

        if dt_celsius > 30.0 or junction_temp > 125.0:
            verdict = "FAILED"
        elif trace_width_mils < req_width_mils or junction_temp > 85.0:
            verdict = "WARNING"
        else:
            verdict = "PASSED"

        summary_str = (
            f"Thermal Analysis: Verdict [{verdict}] | Trace Temp Rise: +{dt_celsius:.1f}°C (Req Min Width: {req_width_mils:.1f} mil) | "
            f"Regulator Junction Temp: {junction_temp:.1f}°C (Power Dissipation: {reg_power_watts:.2f}W)."
        )

        return {
            "status": "success",
            "summary": summary_str,
            "data": {
                "verdict": verdict,
                "current_amps": current_amps,
                "trace_width_mils": trace_width_mils,
                "required_width_mils": round(req_width_mils, 2),
                "resistance_milli_ohms": round(resistance_ohms * 1000, 2),
                "power_loss_milli_watts": round(power_loss_watts * 1000, 2),
                "temp_rise_celsius": round(dt_celsius, 2),
                "regulator_junction_temp_celsius": round(junction_temp, 2),
                "regulator_power_watts": round(reg_power_watts, 2)
            }
        }
    except Exception as e:
        logger.error(f"[calculate_thermal_loss Error] {e}")
        return {
            "status": "error",
            "summary": f"Error calculating thermal loss: {e}",
            "data": {"verdict": "FAILED", "error": str(e)}
        }
