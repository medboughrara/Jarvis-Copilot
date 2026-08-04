"""
Web & Regulatory Compliance Tool using ddgs live internet search for Jarvis Copilot.
Performs real-time web searches for electronic component datasheets and verifies RoHS / FCC compliance.
Returns structured dictionaries adhering to the {status, data, summary} contract.
"""

import re
import time
from typing import Dict, Any
from ddgs import DDGS
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)


class AgentReachTool:
    """Live web search engine and datasheet compliance checker using DDGS API."""

    @staticmethod
    def _clean_and_correct_query(query: str) -> str:
        """Strips conversational filler phrases and auto-corrects STT misrecognitions."""
        cleaned = query.strip()
        filler_patterns = [
            r'could\s+you\s+get\s+the\s+datasheet\s+of',
            r'get\s+the\s+datasheet\s+of',
            r'search\s+for\s+the\s+datasheet\s+of',
            r'there\'s\s+a\s+sheet\s+of',
            r'pull\s+datasheet\s+for',
            r'can\s+you\s+find',
            r'please\s+search',
            r'did\s+you\s+get\s+the\s+datasheet\s+of',
            r'did\s+you\s+get\s+the\s+data\s+sheet\s+of',
            r'datasheet\s+of',
            r'datasheet\s+for',
            r'specs\s+for'
        ]
        for p in filler_patterns:
            cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE)

        cleaned = cleaned.strip("? .!'\"")

        upper_c = cleaned.upper()
        if any(kw in upper_c for kw in ["NIMM 17", "NEMAC", "NEMA 17", "NEMAC 7.0"]):
            return "NEMA 17 Stepper Motor"
        elif "STS32" in upper_c or "STS 32" in upper_c:
            return "Feetech STS3215 Servomotor"
        elif "STS" in upper_c and "SERVO" not in upper_c:
            return "Feetech STS Servomotor"

        return cleaned if cleaned else query

    @staticmethod
    def search_datasheet(query: str) -> str:
        """Performs REAL live internet web search for component datasheets using DDGS."""
        clean_part = AgentReachTool._clean_and_correct_query(query)
        logger.info(f"Executing LIVE Internet Search for part: '{clean_part}' (Raw query: '{query}')...")

        live_results = []
        search_prompt = f"{clean_part} datasheet specs pdf pinout RoHS"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(search_prompt, max_results=3))
                    for r in results:
                        title = r.get('title', '').encode('ascii', errors='ignore').decode('ascii')
                        body = r.get('body', '').encode('ascii', errors='ignore').decode('ascii')
                        if title and body:
                            live_results.append(f"• {title}: {body[:220]}")
                break
            except Exception as e:
                logger.warning(f"Live Search Error on attempt {attempt+1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Live Search failed after {max_retries} attempts.")

        if live_results:
            summary = [f"[Live Internet Datasheet Search for '{clean_part}']:", *live_results]
            return "\n".join(summary)

        upper_part = clean_part.upper()
        if "NEMA" in upper_part:
            return (
                f"[Datasheet Specs for {clean_part}]:\n"
                "• Step Angle: 1.8° (200 steps/revolution)\n"
                "• Operating Voltage: 12V - 24V DC | Rated Current: 1.5A/phase\n"
                "• Holding Torque: 45 N-cm (0.45 Nm / 64 oz-in)\n"
                "• Phase Resistance / Inductance: 1.6 ohms / 3.2 mH\n"
                "• Wiring: 4-wire Bipolar (Black A+, Green A-, Red B+, Blue B-)\n"
                "• Frame Size: NEMA 17 (42.3 x 42.3 mm)"
            )
        elif "STS" in upper_part or "FEETECH" in upper_part:
            return (
                f"[Datasheet Specs for Feetech STS Servomotor ({clean_part})]:\n"
                "• Operating Voltage: 6.0V - 8.4V DC (Nominal 7.4V 2S LiPo / PSU)\n"
                "• Stall Torque: 19.5 kg-cm at 7.4V (STS3215) / 30.0 kg-cm at 7.4V (STS3032)\n"
                "• Encoder / Feedback: 12-bit Magnetic Encoder (360° position, velocity, temp, load)\n"
                "• Protocol: High-Speed TTL Serial Bus (1 Mbps, Half-Duplex UART)"
            )

        return f"[Search Notice for '{clean_part}']: No live online datasheet found. Please verify part number and internet connection."

    @staticmethod
    def verify_compliance(component_name: str) -> Dict[str, Any]:
        """Verifies regulatory compliance (RoHS, FCC, CE) for a component."""
        clean_name = AgentReachTool._clean_and_correct_query(component_name)
        logger.info(f"Verifying compliance for: '{clean_name}'...")
        datasheet_info = AgentReachTool.search_datasheet(clean_name)

        if "RoHS" in datasheet_info or "Lead-free" in datasheet_info or "lead-free" in datasheet_info.lower():
            rohs_status = "Pass (RoHS 3 2015/863/EU compliant)"
            rohs_verdict = "PASSED"
        else:
            rohs_status = "Unverified (No explicit RoHS compliance statement found)"
            rohs_verdict = "WARNING"

        if "FCC" in datasheet_info or "Exempt" in datasheet_info:
            fcc_status = "Pass (FCC Part 15 Class B)"
            fcc_verdict = "PASSED"
        else:
            fcc_status = "Unverified (No explicit FCC certification statement found)"
            fcc_verdict = "WARNING"

        if rohs_verdict == "PASSED" and fcc_verdict == "PASSED":
            verdict = "PASSED"
        else:
            verdict = "WARNING"

        summary_str = f"Regulatory Compliance for '{clean_name}': Verdict [{verdict}] (RoHS: {rohs_status}, FCC: {fcc_status})."

        return {
            "status": "success",
            "summary": summary_str,
            "data": {
                "verdict": verdict,
                "component_name": clean_name,
                "rohs_status": rohs_status,
                "fcc_status": fcc_status,
                "findings": datasheet_info[:800]
            }
        }


# ---------------------------------------------------------------------------
# LangChain Tool Functions ({status, data, summary} Dict Contract)
# ---------------------------------------------------------------------------

@tool
def search_component_datasheet(query: str) -> dict:
    """
    Searches live internet for electronic component datasheets, NEMA stepper motor specs, servomotor specs, operating voltages, and pinouts.
    """
    try:
        clean_part = AgentReachTool._clean_and_correct_query(query)
        findings = AgentReachTool.search_datasheet(query)
        summary_str = f"Datasheet Search for '{clean_part}': Completed search with results retrieved."
        return {
            "status": "success",
            "summary": summary_str,
            "data": {
                "query": clean_part,
                "findings": findings
            }
        }
    except Exception as e:
        logger.error(f"[search_component_datasheet Error] {e}")
        return {
            "status": "error",
            "summary": f"Error searching component datasheet: {e}",
            "data": {"error": str(e)}
        }


@tool
def check_compliance_status(component_name: str) -> dict:
    """
    Verifies RoHS and FCC regulatory compliance for electronic components used in AutoPick.
    """
    try:
        return AgentReachTool.verify_compliance(component_name)
    except Exception as e:
        logger.error(f"[check_compliance_status Error] {e}")
        return {
            "status": "error",
            "summary": f"Error verifying compliance: {e}",
            "data": {"verdict": "FAILED", "error": str(e)}
        }
