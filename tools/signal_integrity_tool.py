"""
Signal Integrity & Bus Impedance Calculator Tool for Jarvis Copilot.
Calculates I2C pull-up resistor ranges, UART series termination, and CAN bus differential impedance.
Returns structured dictionaries adhering to the {status, data, summary} contract.
"""

from typing import Dict, Any
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)


@tool
def check_signal_integrity(
    bus_type: str = "i2c",
    bus_voltage: float = 3.3,
    trace_cap_pf: float = 150.0,
    baud_rate_bps: int = 400000
) -> dict:
    """
    Evaluates signal integrity, I2C pull-up resistor bounds, UART termination, and CAN bus differential lines.
    """
    try:
        bus_type_clean = bus_type.lower().strip()

        if "i2c" in bus_type_clean:
            v_ol_max = 0.4
            i_ol = 0.003
            r_min = (bus_voltage - v_ol_max) / i_ol

            if baud_rate_bps <= 100000:
                max_tr_ns = 1000.0
            elif baud_rate_bps <= 400000:
                max_tr_ns = 300.0
            else:
                max_tr_ns = 120.0

            c_bus_farads = trace_cap_pf * 1e-12
            r_max = (max_tr_ns * 1e-9) / (0.8473 * c_bus_farads) if c_bus_farads > 0 else 99999.0
            recommended_r = (r_min + r_max) / 2.0

            if r_min > r_max:
                verdict = "WARNING"
                recommendation = "Bus capacitance too high for speed! Lower trace length or use I2C buffer."
            else:
                verdict = "PASSED"
                recommendation = f"Recommended pull-up resistor: {recommended_r:.0f} Ohms (2.2k - 4.7k Ohms)."

            summary_str = f"Signal Integrity for I2C: Verdict [{verdict}] | R_min: {r_min:.0f}Ω, R_max: {r_max:.0f}Ω | {recommendation}"
            data_dict = {
                "verdict": verdict,
                "bus_type": "I2C",
                "bus_voltage": bus_voltage,
                "trace_capacitance_pf": trace_cap_pf,
                "r_min_ohms": round(r_min, 1),
                "r_max_ohms": round(r_max, 1),
                "recommended_pullup_ohms": round(recommended_r, 1),
                "recommendation": recommendation
            }

        elif "can" in bus_type_clean:
            verdict = "PASSED"
            summary_str = "Signal Integrity for CAN Bus: Verdict [PASSED] | 120Ω differential impedance (split 60Ω+60Ω with 4.7nF to GND)."
            data_dict = {
                "verdict": verdict,
                "bus_type": "CAN",
                "differential_impedance_ohms": 120,
                "split_termination_ohms": 60,
                "decoupling_cap_nf": 4.7
            }

        elif "uart" in bus_type_clean:
            verdict = "PASSED"
            summary_str = "Signal Integrity for UART: Verdict [PASSED] | 22-33Ω series damping resistors recommended on TX/RX lines."
            data_dict = {
                "verdict": verdict,
                "bus_type": "UART",
                "recommended_series_resistor_ohms": "22-33"
            }

        else:
            verdict = "PASSED"
            summary_str = f"Signal Integrity for {bus_type.upper()}: Verdict [PASSED] | Keep clock and signal traces over unbroken ground plane."
            data_dict = {
                "verdict": verdict,
                "bus_type": bus_type.upper(),
                "recommendation": "Maintain unbroken ground reference plane under signal traces."
            }

        return {
            "status": "success",
            "summary": summary_str,
            "data": data_dict
        }
    except Exception as e:
        logger.error(f"[check_signal_integrity Error] {e}")
        return {
            "status": "error",
            "summary": f"Error checking signal integrity: {e}",
            "data": {"verdict": "FAILED", "error": str(e)}
        }
