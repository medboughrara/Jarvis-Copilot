"""
🛡️ Level 2 Transport: Anti-Bot TLS Impersonation (curl_cffi) for Jarvis MCP Gateway (Phase 3).

Uses curl_cffi to impersonate real browser TLS fingerprints (JA3/JA4, HTTP/2 settings,
Akamai & Cloudflare bypass) without running a heavy headless browser.
"""

import asyncio
import logging
from typing import Dict, Any
from curl_cffi import requests as cffi_requests
import config
from gateway.cleaner import clean_html_to_markdown

logger = config.get_logger(__name__)


def _sync_antibot_get(url: str, impersonate_browser: str, timeout_seconds: float):
    with cffi_requests.Session(impersonate=impersonate_browser) as s:
        return s.get(url, timeout=timeout_seconds, allow_redirects=True)


async def antibot_fetch(url: str, impersonate_browser: str = "chrome124", timeout_seconds: float = 15.0) -> Dict[str, Any]:
    """
    Executes an anti-bot HTTP GET request using curl_cffi TLS impersonation.
    Bypasses Cloudflare, DataDome, and TLS-fingerprinting bot guards.
    """
    logger.info(f"[Anti-Bot Transport] Fetching with '{impersonate_browser}' TLS fingerprint: '{url}'")
    try:
        resp = await asyncio.to_thread(_sync_antibot_get, url, impersonate_browser, timeout_seconds)
        
        if resp.status_code in [403, 429, 503]:
            # Try Safari fingerprint fallback
            if impersonate_browser != "safari17_0":
                logger.info(f"[Anti-Bot Transport] Retrying with Safari 17 TLS profile...")
                return await antibot_fetch(url, impersonate_browser="safari17_0", timeout_seconds=timeout_seconds)

            return {
                "success": False,
                "status_code": resp.status_code,
                "error": f"Anti-bot TLS blocked (HTTP {resp.status_code})",
                "requires_js_render": True
            }

        html = resp.text
        lower_html = html.lower()
        if any(marker in lower_html for marker in ["cf-challenge", "checking your browser", "turnstile", "interstitial"]):
            logger.warning(f"[Anti-Bot Transport] JS-based Cloudflare challenge active on '{url}'")
            return {
                "success": False,
                "status_code": resp.status_code,
                "error": "Interactive JS challenge required",
                "requires_js_render": True
            }

        markdown = clean_html_to_markdown(html, base_url=url)
        return {
            "success": True,
            "status_code": resp.status_code,
            "url": str(resp.url),
            "markdown": markdown,
            "content_length": len(markdown),
            "transport": "antibot_curl_cffi"
        }

    except Exception as e:
        logger.warning(f"[Anti-Bot Transport] Error: {e}")
        return {
            "success": False,
            "status_code": 0,
            "error": str(e),
            "requires_js_render": True
        }
