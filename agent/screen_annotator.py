"""
Screen Annotator & Holographic Spotlight Overlay for Jarvis Copilot.
Manages the fullscreen transparent overlay canvas that renders glowing spotlight rings,
laser pointing vectors, and visual HUD bounding boxes over on-screen targets.

Hardened Features:
- Task 4: Exclusive Fullscreen Transition Invalidation (clears stale coordinates on display mode switch).
- Task 7: Heartbeat Timeout Self-Clear Watchdog (auto-purges annotations if pet process crashes).
- Configurable annotation lease and smooth fadeout animations.
"""

import time
from typing import Dict, Any, List, Optional
import config

logger = config.get_logger(__name__)


class ScreenAnnotator:
    """Manages active visual screen annotations, spotlights, and self-healing watchdogs."""

    def __init__(self, heartbeat_timeout: float = 5.0):
        self.active_annotations: List[Dict[str, Any]] = []
        self.last_heartbeat_time: float = time.time()
        self.heartbeat_timeout: float = heartbeat_timeout
        self.is_fullscreen_suppressed: bool = False

    def record_heartbeat(self, timestamp: Optional[float] = None) -> None:
        """Updates the parent pet process heartbeat timestamp."""
        self.last_heartbeat_time = timestamp or time.time()

    def check_heartbeat_watchdog(self, current_time: Optional[float] = None) -> bool:
        """
        Task 7 Self-Clear Watchdog:
        If no heartbeat has been received within heartbeat_timeout, automatically
        clears all active annotations to prevent stuck visual artifacts on screen.
        Returns True if self-cleared, False otherwise.
        """
        now = current_time or time.time()
        if self.active_annotations and (now - self.last_heartbeat_time > self.heartbeat_timeout):
            count = len(self.active_annotations)
            self.clear_annotations()
            logger.warning(
                f"[Screen Annotator Watchdog] Heartbeat expired ({now - self.last_heartbeat_time:.1f}s > {self.heartbeat_timeout}s). "
                f"Auto-cleared {count} orphaned annotation(s)."
            )
            return True
        return False

    def on_fullscreen_transition(self, is_fullscreen: bool) -> None:
        """
        Task 4 Fullscreen Invalidation:
        On any exclusive fullscreen transition (game, video, KiCad fullscreen),
        immediately invalidates and purges all active annotations.
        """
        self.is_fullscreen_suppressed = is_fullscreen
        if self.active_annotations:
            count = len(self.active_annotations)
            self.clear_annotations()
            logger.info(
                f"[Screen Annotator] Exclusive fullscreen mode {'entered' if is_fullscreen else 'exited'}. "
                f"Invalidated {count} pending annotation(s)."
            )

    def add_spotlight(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        label: str = "",
        color: str = "#00f2ff",
        duration: float = 5.0,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """Adds a holographic glowing spotlight ring at target coordinates."""
        now = timestamp or time.time()
        # Reset heartbeat upon new command
        self.record_heartbeat(now)

        if self.is_fullscreen_suppressed:
            logger.info(f"[Screen Annotator] Suppressed spotlight for '{label}' due to fullscreen mode.")
            return {"status": "suppressed", "reason": "fullscreen_active"}

        annotation = {
            "id": f"ann_{int(now * 1000)}",
            "type": "spotlight_ring",
            "x": int(x),
            "y": int(y),
            "width": int(width),
            "height": int(height),
            "label": label,
            "color": color,
            "created_at": now,
            "expires_at": now + duration,
            "duration": duration
        }
        self.active_annotations.append(annotation)
        logger.info(f"[Screen Annotator] Rendered spotlight at ({x}, {y}) for '{label}'.")
        return {"status": "success", "annotation": annotation}

    def clear_annotations(self) -> None:
        """Clears all active annotations from the overlay canvas."""
        self.active_annotations.clear()

    def get_active_annotations(self, current_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """Returns list of unexpired active annotations, purging expired ones."""
        now = current_time or time.time()
        self.check_heartbeat_watchdog(now)
        self.active_annotations = [a for a in self.active_annotations if a["expires_at"] > now]
        return list(self.active_annotations)


# Global Singleton Screen Annotator
screen_annotator = ScreenAnnotator()
