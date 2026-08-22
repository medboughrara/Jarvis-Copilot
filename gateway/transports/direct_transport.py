"""
🚀 Level 1 Transport: Direct Fast HTTP Fetch for Jarvis MCP Gateway.

Uses lightweight, high-performance async HTTP (HTTPX / Aiohttp) and converts
raw HTML into structured, LLM-ready Markdown.
"""

import re
import httpx
import logging
from typing import Dict, Any, Tuple
import config
from gateway.cleaner import clean_html_to_markdown

logger = config.get_logger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}


async def direct_fetch(url: str, timeout_seconds: float = 10.0) -> Dict[str, Any]:
    """
    Executes a direct async HTTP GET request and returns clean Markdown.
    Returns error metadata if request is blocked or requires anti-bot bypass.
    """
    logger.info(f"[Direct Transport] Fetching: '{url}'")
    try:
        async with httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=timeout_seconds, follow_redirects=True) as client:
            resp = await client.get(url)
            
            # Check for bot block or rate limit
            if resp.status_code in [403, 429, 503]:
                logger.warning(f"[Direct Transport] Blocked on '{url}' with HTTP {resp.status_code}")
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": f"HTTP {resp.status_code} Blocked",
                    "requires_escalation": True
                }

            html = resp.text
            # Check for Cloudflare / bot detection markers
            lower_html = html.lower()
            if any(marker in lower_html for marker in ["cf-challenge", "checking your browser", "just a moment...", "turnstile", "captcha", "security check"]):
                logger.warning(f"[Direct Transport] Bot challenge detected in HTML on '{url}'")
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": "Anti-bot challenge detected",
                    "requires_escalation": True
                }

            # Check if page is an empty client-side SPA shell needing JS rendering
            if len(html) < 600 and ("id=\"app\"" in lower_html or "id=\"root\"" in lower_html or "<noscript>" in lower_html):
                logger.warning(f"[Direct Transport] SPA shell detected on '{url}' (needs JS rendering)")
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": "Dynamic JavaScript SPA required",
                    "requires_js_render": True
                }

            markdown = clean_html_to_markdown(html, base_url=url)
            return {
                "success": True,
                "status_code": resp.status_code,
                "url": str(resp.url),
                "markdown": markdown,
                "content_length": len(markdown),
                "transport": "direct_fetch"
            }

    except httpx.HTTPError as he:
        logger.warning(f"[Direct Transport] Network error on '{url}': {he}")
        return {
            "success": False,
            "status_code": 0,
            "error": str(he),
            "requires_escalation": True
        }
    except Exception as e:
        logger.error(f"[Direct Transport] Unexpected error: {e}")
        return {
            "success": False,
            "status_code": 0,
            "error": str(e),
            "requires_escalation": True
        }
