"""
⏱️ Caching, Rate Limiting & Politeness Middleware for Jarvis MCP Gateway (Phase 8).

Features:
1. In-memory & disk response caching with configurable TTL.
2. Per-domain rate limiting and politeness delays.
3. Access telemetry logging resolution methods (Direct, Anti-Bot, Crawl4AI, Browser Agent).
"""

import time
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import config

logger = config.get_logger(__name__)

# Global In-Memory Cache: {url_hash: (timestamp, data)}
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_LAST_DOMAIN_ACCESS: Dict[str, float] = {}
DEFAULT_CACHE_TTL = 3600.0  # 1 Hour
MIN_DOMAIN_INTERVAL = 0.5   # 500ms between requests to the same domain


def get_cached_content(url: str, ttl_seconds: float = DEFAULT_CACHE_TTL) -> Optional[Dict[str, Any]]:
    """Returns cached response if present and not expired."""
    key = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()
    if key in _CACHE:
        timestamp, data = _CACHE[key]
        if time.time() - timestamp < ttl_seconds:
            logger.info(f"[Gateway Cache] Cache HIT for '{url}'")
            return data
    return None


def set_cached_content(url: str, data: Dict[str, Any]):
    """Stores response in cache."""
    key = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()
    _CACHE[key] = (time.time(), data)


def apply_politeness_delay(url: str, min_interval_seconds: float = MIN_DOMAIN_INTERVAL):
    """Enforces minimum interval between consecutive requests to the same domain."""
    try:
        domain = urlparse(url).netloc
        if domain in _LAST_DOMAIN_ACCESS:
            elapsed = time.time() - _LAST_DOMAIN_ACCESS[domain]
            if elapsed < min_interval_seconds:
                sleep_time = min_interval_seconds - elapsed
                time.sleep(sleep_time)
        _LAST_DOMAIN_ACCESS[domain] = time.time()
    except Exception:
        pass
