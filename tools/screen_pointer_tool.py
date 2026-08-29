"""
Screen Pointer & Interactive Element Grounding Tool for Jarvis Copilot.
Directs the floating Desktop Pet and Screen Annotator overlay to locate, fly to,
and highlight target visual elements (code lines, KiCad components, UI buttons) on the screen.

Structural Guarantees:
- 100% on-device local element grounding via tools.omniparser_tool.locate_screen_element_local_only.
- Strict Pointing-Only Boundary: Only highlights and points gestures; never injects clicks or keystrokes.
- Unified Cancel-and-Replace Policy: Simultaneous transition for both visual flight/spotlight and voice TTS narration.
- Multi-Monitor DPI scaling normalization.
"""

import os
import time
from typing import Dict, Any, Optional, Callable, List, Tuple
from langchain_core.tools import tool
import config
from tools.omniparser_tool import locate_screen_element_local_only

logger = config.get_logger(__name__)


class ScreenPointerManager:
    """Singleton coordinator for screen element pointing, flight animations, and unified interruption."""

    def __init__(self):
        self.current_target: Optional[Dict[str, Any]] = None
        self.active_flight_id: Optional[str] = None
        self.flight_history: List[Dict[str, Any]] = []
        
        # Lifecycle Event Hooks (enables deterministic testing without wall-clock delays)
        self.on_flight_start: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_speech_start: Optional[Callable[[str], None]] = None
        self.on_target_cancelled: Optional[Callable[[Dict[str, Any]], None]] = None

    def normalize_coordinates(
        self,
        physical_x: int,
        physical_y: int,
        dpi_scale: float = 1.0,
        virtual_left: int = 0,
        virtual_top: int = 0
    ) -> Tuple[int, int]:
        """
        Normalizes physical screenshot pixel coordinates to virtual screen logical window coordinates.
        Logical_X = (Physical_X - Virtual_Left) / DPI_Scale
        Logical_Y = (Physical_Y - Virtual_Top) / DPI_Scale
        """
        effective_dpi = dpi_scale if dpi_scale > 0 else 1.0
        logical_x = int((physical_x - virtual_left) / effective_dpi)
        logical_y = int((physical_y - virtual_top) / effective_dpi)
        return logical_x, logical_y

    def point_to_element(
        self,
        target_description: str,
        narration_text: str = "",
        dpi_scale: float = 1.0,
        screenshot_path: Optional[str] = None,
        on_capture_flash: Optional[Callable[[], None]] = None
    ) -> Dict[str, Any]:
        """
        Locates target element via local OCR and dispatches unified visual flight and voice narration.
        Enforces Cancel-and-Replace across both visual and auditory channels simultaneously.
        """
        flight_id = f"flight_{int(time.time() * 1000)}"

        # 1. Cancel previous active sequence across both voice and visual channels
        if self.current_target is not None:
            old_target = self.current_target
            logger.info(f"[Screen Pointer] Interrupting prior target '{old_target.get('query')}' with '{target_description}'.")
            if self.on_target_cancelled:
                self.on_target_cancelled(old_target)

        # 2. Local-Only OCR Element Resolution (Zero Network Calls)
        resolved = locate_screen_element_local_only(
            query=target_description,
            dpi_scale=dpi_scale,
            screenshot_path=screenshot_path,
            on_capture_callback=on_capture_flash
        )

        if not resolved:
            return {
                "status": "error",
                "message": f"Could not resolve screen coordinates for '{target_description}'."
            }

        # 3. Compute Normalized Logical Coordinates
        log_x, log_y = self.normalize_coordinates(resolved["center_x"], resolved["center_y"], dpi_scale)

        target_payload = {
            "flight_id": flight_id,
            "query": target_description,
            "physical_x": resolved["center_x"],
            "physical_y": resolved["center_y"],
            "logical_x": log_x,
            "logical_y": log_y,
            "width": resolved["w"],
            "height": resolved["h"],
            "confidence": resolved["confidence"],
            "dpi_scale": dpi_scale,
            "narration": narration_text or f"Pointing to {target_description}",
            "timestamp": time.time(),
            "status": "active"
        }

        self.current_target = target_payload
        self.active_flight_id = flight_id
        self.flight_history.append(target_payload)

        # 4. Trigger Unified Lifecycle Hooks
        if self.on_flight_start:
            self.on_flight_start(target_payload)

        if self.on_speech_start:
            self.on_speech_start(target_payload["narration"])

        return {
            "status": "success",
            "summary": f"Jarvis pointing to '{target_description}' at ({log_x}, {log_y}) [Confidence: {resolved['confidence']*100:.0f}%]",
            "data": target_payload
        }

    def cancel_active_pointing(self) -> Dict[str, Any]:
        """Clears current active pointing target and notifies listeners."""
        if self.current_target:
            old = self.current_target
            self.current_target = None
            self.active_flight_id = None
            if self.on_target_cancelled:
                self.on_target_cancelled(old)
            return {"status": "success", "message": "Screen pointing dismissed."}
        return {"status": "success", "message": "No active pointing target."}


# Global Singleton Screen Pointer Coordinator
screen_pointer_manager = ScreenPointerManager()


# ---------------------------------------------------------------------------
# LangChain Copilot Tools
# ---------------------------------------------------------------------------

@tool
def point_and_highlight_screen_element(target_description: str, message: str = "") -> dict:
    """
    Finds a visual element, code token, or component on the user's screen using local OCR,
    and commands the Desktop Pet to fly to it, point with its arm, and draw a glowing spotlight.
    Strictly visual pointing only — does not click or modify user input.
    """
    res = screen_pointer_manager.point_to_element(
        target_description=target_description,
        narration_text=message
    )
    return res


@tool
def dismiss_screen_annotations() -> dict:
    """
    Clears all active glowing spotlight rings from the screen and returns the Desktop Pet to idle mode.
    """
    return screen_pointer_manager.cancel_active_pointing()
