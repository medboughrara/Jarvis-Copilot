"""
Signal Integrity & Bus Impedance Calculator Tool for Jarvis Copilot.
Calculates I2C pull-up resistor ranges, UART series termination, and CAN bus differential impedance.
"""

from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

@tool
def check_signal_integrity(
    bus_type: str = "i2c",
    bus_voltage: float = 3.3,
    trace_cap_pf: float = 150.0,
    baud_rate_bps: int = 400000
) -> str:
    """
    Evaluates signal integrity, I2C pull-up resistor bounds, UART termination, and CAN bus differential lines.
    
    Args:
        bus_type: Type of communication bus ("i2c", "uart", "can", "spi").
        bus_voltage: Bus operating voltage (e.g. 3.3V or 5V).
        trace_cap_pf: Total bus trace and pin capacitance in picofarads.
        baud_rate_bps: Clock frequency or baud rate in Hz (e.g. 400000 for Fast-mode I2C).
    """
    bus_type = bus_type.lower().strip()
    report = [
        "============================================================",
        f"       AUTOPICK SIGNAL INTEGRITY REPORT: {bus_type.upper()}",
        "============================================================",
        f"Bus Voltage: {bus_voltage:.1f} V | Trace Capacitance: {trace_cap_pf:.1f} pF | Rate: {baud_rate_bps/1000:.1f} kHz"
    ]

    if "i2c" in bus_type:
        # I2C Standard: Vol_max = 0.4V, Iol = 3mA (0.003A)
        v_ol_max = 0.4
        i_ol = 0.003
        r_min = (bus_voltage - v_ol_max) / i_ol

        # Max rise time tr according to I2C spec (1000ns for 100kHz, 300ns for 400kHz, 120ns for 1MHz)
        if baud_rate_bps <= 100000:
            max_tr_ns = 1000.0
        elif baud_rate_bps <= 400000:
            max_tr_ns = 300.0
        else:
            max_tr_ns = 120.0

        c_bus_farads = trace_cap_pf * 1e-12
        r_max = (max_tr_ns * 1e-9) / (0.8473 * c_bus_farads)
        recommended_r = (r_min + r_max) / 2.0

        report.append("------------------------------------------------------------")
        report.append(f"I2C Pull-Up Resistor Calculation:")
        report.append(f"  Minimum Pull-Up (Current Limit): {r_min:.0f} Ohms")
        report.append(f"  Maximum Pull-Up (Rise Time Limit {max_tr_ns:.0f}ns): {r_max:.0f} Ohms")
        report.append(f"  Recommended Standard Value: {recommended_r:.0f} Ohms (e.g. 2.2k - 4.7k Ohms)")

        if r_min > r_max:
            report.append("⚠️ ALERT: Bus capacitance is too high for this speed! Lower trace length or use I2C buffer (PCA9515).")
        else:
            report.append("✅ PASS: Pull-up resistor bounds are valid for this bus capacitance.")

    elif "uart" in bus_type:
        # UART TTL Integrity
        report.append("------------------------------------------------------------")
        report.append("UART Series Damping Resistor Recommendation:")
        report.append("  Recommended Series Resistors on TX/RX: 22 to 33 Ohms near MCU TX pin.")
        report.append("  Purpose: Dampens ringing, edge overshoot, and EMI emissions on long cabling.")

    elif "can" in bus_type:
        # CAN Bus Differential Lines
        report.append("------------------------------------------------------------")
        report.append("CAN Bus Termination Recommendation:")
        report.append("  Differential Impedance: 120 Ohms characteristic impedance.")
        report.append("  Recommended Termination: Split 60 + 60 Ohms with 4.7nF capacitor to GND for noise filtering.")

    else: # SPI or General Digital
        report.append("------------------------------------------------------------")
        report.append("General Digital Bus Recommendation:")
        report.append("  Keep clock (SCK/CLK) and data lines away from high-current motor power traces.")
        report.append("  Use unbroken ground reference plane under signal traces.")

    report.append("============================================================")
    return "\n".join(report)
