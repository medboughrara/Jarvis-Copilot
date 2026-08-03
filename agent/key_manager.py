"""
Gemini API Key Rotation, Usage Tracking, & Rate Limit Management System.
Tracks request counts, error counts, rate limits, and auto-rotates across multiple API keys.
"""

import os
import time
import json
import logging
import config

logger = config.get_logger(__name__)

STATS_FILE = os.path.join("scratch", "gemini_key_stats.json")

class GeminiKeyManager:
    """Manages multi-key rotation, per-key usage metrics tracking, and rate limit cooling."""

    def __init__(self, api_keys: list[str] = None):
        if not api_keys:
            raw_keys = os.getenv("GEMINI_API_KEYS", "")
            if raw_keys:
                api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
            else:
                single_key = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
                api_keys = [single_key] if single_key else []

        self.api_keys = api_keys
        self.current_index = 0
        self.stats = {}
        
        self._load_stats()

    def _load_stats(self):
        """Loads usage statistics from disk JSON if available."""
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r") as f:
                    self.stats = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load key stats JSON: {e}")
                self.stats = {}

        # Ensure all registered keys have stat entries
        for key in self.api_keys:
            masked_key = self._mask_key(key)
            if masked_key not in self.stats:
                self.stats[masked_key] = {
                    "request_count": 0,
                    "error_count": 0,
                    "last_used": 0,
                    "rate_limited_until": 0,
                    "status": "ACTIVE"
                }

    def _save_stats(self):
        """Persists tracking statistics to scratch/gemini_key_stats.json."""
        os.makedirs("scratch", exist_ok=True)
        try:
            with open(STATS_FILE, "w") as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save key stats JSON: {e}")

    @staticmethod
    def _mask_key(key: str) -> str:
        """Returns a safe masked version of the API key for display/logging."""
        if not key or len(key) < 10:
            return "INVALID_KEY"
        return f"{key[:8]}...{key[-4:]}"

    def get_working_key(self) -> str | None:
        """
        Returns the next available, non-rate-limited API key using round-robin rotation.
        Returns None if all keys are currently rate-limited or exhausted.
        """
        if not self.api_keys:
            return None

        now = time.time()
        num_keys = len(self.api_keys)

        # Check all keys starting from current_index
        for i in range(num_keys):
            idx = (self.current_index + i) % num_keys
            key = self.api_keys[idx]
            masked = self._mask_key(key)
            key_stat = self.stats.get(masked, {})

            # Check if key is currently rate-limited
            rate_limited_until = key_stat.get("rate_limited_until", 0)
            if now < rate_limited_until:
                remaining_cooldown = int(rate_limited_until - now)
                logger.info(f"Skipping key {masked}: rate-limited for {remaining_cooldown}s more.")
                continue

            # Key is available! Update index and return
            self.current_index = (idx + 1) % num_keys
            return key

        logger.warning("All Gemini API keys are currently rate-limited or exhausted!")
        return None

    def report_success(self, key: str):
        """Records a successful API call for the given key."""
        masked = self._mask_key(key)
        if masked not in self.stats:
            self.stats[masked] = {"request_count": 0, "error_count": 0, "last_used": 0, "rate_limited_until": 0, "status": "ACTIVE"}

        self.stats[masked]["request_count"] += 1
        self.stats[masked]["last_used"] = int(time.time())
        self.stats[masked]["status"] = "ACTIVE"
        self._save_stats()

    def report_error(self, key: str, is_rate_limit: bool = True, cooldown_seconds: int = 60):
        """Records an error/rate-limit for the key and places it in cooling penalty."""
        masked = self._mask_key(key)
        if masked not in self.stats:
            self.stats[masked] = {"request_count": 0, "error_count": 0, "last_used": 0, "rate_limited_until": 0, "status": "ACTIVE"}

        self.stats[masked]["error_count"] += 1
        if is_rate_limit:
            self.stats[masked]["rate_limited_until"] = int(time.time() + cooldown_seconds)
            self.stats[masked]["status"] = f"RATE_LIMITED_{cooldown_seconds}s"
        else:
            self.stats[masked]["status"] = "ERROR"

        logger.warning(f"Reported error for key {masked}. Status set to: {self.stats[masked]['status']}")
        self._save_stats()

    def get_usage_summary(self) -> str:
        """Returns a human-readable tracking summary table of all API keys."""
        if not self.api_keys:
            return "No Gemini API keys registered."

        now = time.time()
        lines = [
            "============================================================",
            "        GEMINI API KEY TRACKING & USAGE SUMMARY",
            "============================================================",
            f"{'Key ID':<18} | {'Requests':<10} | {'Errors':<8} | {'Status':<16} | {'Last Used'}",
            "------------------------------------------------------------"
        ]

        for key in self.api_keys:
            masked = self._mask_key(key)
            stat = self.stats.get(masked, {})
            reqs = stat.get("request_count", 0)
            errs = stat.get("error_count", 0)
            last_used_ts = stat.get("last_used", 0)
            rate_until = stat.get("rate_limited_until", 0)

            if now < rate_until:
                status_str = f"RATE_LIMITED ({int(rate_until - now)}s)"
            else:
                status_str = stat.get("status", "ACTIVE")

            if last_used_ts > 0:
                time_ago = f"{int(now - last_used_ts)}s ago"
            else:
                time_ago = "Never"

            lines.append(f"{masked:<18} | {reqs:<10} | {errs:<8} | {status_str:<16} | {time_ago}")

        lines.append("============================================================")
        return "\n".join(lines)
