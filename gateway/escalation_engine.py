"""
🎯 Escalation Engine for Jarvis MCP Web Gateway (Phase 5).

Unified Entry Point: get_web_content(url)
Executes an intelligent 4-tier escalation ladder:
1. Direct Fast Fetch (HTTPX / Aiohttp)
2. Anti-Bot TLS Impersonation (curl_cffi JA3/JA4)
3. Crawl4AI / Playwright Dynamic JS Render
4. Autonomous Browser Agent (Gemini Controller)
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional
import config
from gateway.transports.direct_transport import direct_fetch
from gateway.transports.antibot_transport import antibot_fetch
from gateway.transports.crawl4ai_transport import crawl4ai_fetch
from gateway.transports.browser_agent import execute_browser_task
from gateway.cache_and_politeness import (
    get_cached_content,
    set_cached_content,
    apply_politeness_delay
)

logger = config.get_logger(__name__)


async def fetch_web_content_escalated(
    url: str,
    force_method: Optional[str] = None,
    bypass_cache: bool = False
) -> Dict[str, Any]:
    """
    Fetches web content with automatic anti-bot, JS rendering, and browser agent escalation.

    Args:
        url: Target web URL or domain.
        force_method: Optional override: 'direct_fetch', 'antibot_curl_cffi', 'crawl4ai_render', 'browser_agent'.
        bypass_cache: If True, bypasses local TTL cache.

    Returns:
        dict containing clean Markdown content, resolution method, and status.
    """
    clean_url = url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        clean_url = "https://" + clean_url

    start_time = time.time()

    # 1. Check Local Cache
    if not bypass_cache and not force_method:
        cached = get_cached_content(clean_url)
        if cached:
            cached["cached"] = True
            cached["latency_ms"] = round((time.time() - start_time) * 1000, 1)
            return cached

    # Apply politeness delay before hit
    apply_politeness_delay(clean_url)

    logger.info(f"[Escalation Engine] Initiating fetch for: '{clean_url}' (forced={force_method})")

    # Override handling
    if force_method == "antibot_curl_cffi":
        res = await antibot_fetch(clean_url)
        if res.get("success"):
            return _package_result(res, start_time, clean_url)
    elif force_method == "crawl4ai_render":
        res = await crawl4ai_fetch(clean_url)
        if res.get("success"):
            return _package_result(res, start_time, clean_url)
    elif force_method == "browser_agent":
        res = await execute_browser_task(f"Extract main content from {clean_url}", start_url=clean_url)
        return _package_result(res, start_time, clean_url)

    # -------------------------------------------------------------------------
    # Tier 1: Direct Fast Fetch
    # -------------------------------------------------------------------------
    res1 = await direct_fetch(clean_url)
    if res1.get("success"):
        logger.info(f"[Escalation Engine] Resolved '{clean_url}' via Tier 1 (Direct Fetch)")
        return _package_result(res1, start_time, clean_url)

    # -------------------------------------------------------------------------
    # Tier 2: Anti-Bot TLS Impersonation (curl_cffi)
    # -------------------------------------------------------------------------
    if res1.get("requires_escalation") or res1.get("status_code") in [403, 429, 503]:
        logger.info(f"[Escalation Engine] Escalating '{clean_url}' to Tier 2 (curl_cffi anti-bot)...")
        res2 = await antibot_fetch(clean_url)
        if res2.get("success"):
            logger.info(f"[Escalation Engine] Resolved '{clean_url}' via Tier 2 (curl_cffi)")
            return _package_result(res2, start_time, clean_url)

    # -------------------------------------------------------------------------
    # Tier 3: Crawl4AI / Playwright Dynamic JS Render
    # -------------------------------------------------------------------------
    logger.info(f"[Escalation Engine] Escalating '{clean_url}' to Tier 3 (Crawl4AI / JS Render)...")
    res3 = await crawl4ai_fetch(clean_url)
    if res3.get("success"):
        logger.info(f"[Escalation Engine] Resolved '{clean_url}' via Tier 3 (Crawl4AI)")
        return _package_result(res3, start_time, clean_url)

    # -------------------------------------------------------------------------
    # Tier 4: Autonomous Browser Agent
    # -------------------------------------------------------------------------
    logger.info(f"[Escalation Engine] Escalating '{clean_url}' to Tier 4 (Autonomous Browser Agent)...")
    res4 = await execute_browser_task(f"Extract main content from {clean_url}", start_url=clean_url)
    if res4.get("success"):
        logger.info(f"[Escalation Engine] Resolved '{clean_url}' via Tier 4 (Browser Agent)")
        return _package_result(res4, start_time, clean_url)

    # Fallback Failure
    return {
        "status": "error",
        "url": clean_url,
        "resolved_by": "none",
        "error": res1.get("error") or res3.get("error") or "All escalation tiers failed",
        "latency_ms": round((time.time() - start_time) * 1000, 1)
    }


def _package_result(res: Dict[str, Any], start_time: float, url: str) -> Dict[str, Any]:
    """Helper packaging standardized result dictionary and caching."""
    markdown_content = res.get("markdown") or res.get("result") or ""
    resolved_by = res.get("transport", "unknown")
    latency_ms = round((time.time() - start_time) * 1000, 1)

    result = {
        "status": "success",
        "url": url,
        "resolved_by": resolved_by,
        "content_type": "markdown",
        "markdown": markdown_content,
        "content_length": len(markdown_content),
        "latency_ms": latency_ms
    }

    set_cached_content(url, result)
    return result
