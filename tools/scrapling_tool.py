"""
🕷️ Scrapling Adaptive Web Scraping & Stealth Data Extraction Tool for Jarvis AI Assistant.

Integrates the official Scrapling framework (https://github.com/d4vinci/Scrapling):
1. Stealthy Fetching: Bypasses Cloudflare Turnstile, anti-bot protections, and TLS fingerprinting.
2. Adaptive Element Relocation: Learns from website changes to survive design/DOM redesigns.
3. Dynamic JS Execution: Headless browser rendering with network idle wait and ad blocking.
4. AI-Targeted Extraction: Sanitizes HTML and exports clean, readable Markdown for LLMs.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)


def _html_to_clean_markdown(html_content: Any, title: str = "") -> str:
    """Helper to convert HTML to clean markdown."""
    text_input = str(html_content) if html_content is not None else ""
    if not text_input.strip():
        return ""
    try:
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_tables = False
        h.body_width = 0
        return h.handle(text_input).strip()
    except ImportError:
        # Fast regex cleaner
        cleaned = re.sub(r'<script.*?</script>', '', text_input, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<style.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned[:8000]


@tool
def scrape_web_page(
    url: str,
    mode: str = "fast",
    css_selector: str = "",
    ai_targeted: bool = True
) -> dict:
    """
    Scrapes any web page using Scrapling with anti-bot bypass, Cloudflare Turnstile solving, and stealth headers.

    Args:
        url: The web page URL to scrape.
        mode: Scraping engine mode: 'fast' (HTTP TLS impersonation), 'stealth' (anti-bot bypass browser), or 'dynamic' (Playwright JS browser).
        css_selector: Optional CSS selector to extract specific elements (e.g. 'article', '.quote', '#main', '.quote .text::text').
        ai_targeted: Whether to clean clutter/ads and extract clean text/markdown for AI consumption.

    Returns:
        dict containing status, summary, extracted content (markdown/text), and page metadata.
    """
    url_clean = url.strip()
    if not url_clean.startswith("http://") and not url_clean.startswith("https://"):
        url_clean = f"https://{url_clean}"

    logger.info(f"[Scrapling] Scraping '{url_clean}' in mode '{mode}' (selector='{css_selector}')")

    try:
        from scrapling.fetchers import Fetcher, StealthyFetcher, PlayWrightFetcher
        from scrapling.parser import Adaptor

        mode_lower = mode.lower().strip()
        page = None
        fetcher_used = ""

        if mode_lower in ["stealth", "cloudflare", "camoufox", "antibot"]:
            fetcher_used = "StealthyFetcher (Camoufox Anti-Bot)"
            try:
                page = StealthyFetcher.fetch(url_clean, headless=True)
            except Exception as se:
                logger.warning(f"[Scrapling] StealthyFetcher fallback to Fetcher: {se}")
                page = Fetcher.get(url_clean, stealthy_headers=True, timeout=25)
                fetcher_used = "Fetcher (Fallback)"
        elif mode_lower in ["dynamic", "js", "playwright"]:
            fetcher_used = "PlayWrightFetcher (Headless JS)"
            try:
                page = PlayWrightFetcher.fetch(url_clean, headless=True)
            except Exception as pe:
                logger.warning(f"[Scrapling] PlayWrightFetcher fallback to Fetcher: {pe}")
                page = Fetcher.get(url_clean, stealthy_headers=True, timeout=25)
                fetcher_used = "Fetcher (Fallback)"
        else:
            # Default to fast stealthy HTTP Fetcher
            fetcher_used = "Fetcher (HTTP Chrome TLS)"
            page = Fetcher.get(url_clean, stealthy_headers=True, timeout=25)

        # Extract target elements if selector provided
        extracted_text = ""
        matched_count = 0

        if css_selector and css_selector.strip():
            sel = css_selector.strip()
            elements = page.css(sel)
            
            # Handle TextHandlers vs Adaptor elements
            if hasattr(elements, "get_all"):
                items = elements.get_all()
                matched_count = len(items)
                extracted_text = "\n\n".join([str(it) for it in items[:30]])
            elif isinstance(elements, list) or hasattr(elements, "__len__"):
                matched_count = len(elements)
                snippets = []
                for el in elements[:25]:
                    if hasattr(el, "get_all"):
                        snippets.extend(el.get_all())
                    elif hasattr(el, "text") and el.text:
                        snippets.append(str(el.text))
                    elif hasattr(el, "get"):
                        snippets.append(str(el.get()))
                    else:
                        snippets.append(str(el))
                extracted_text = "\n\n".join([s.strip() for s in snippets if str(s).strip()])
            else:
                extracted_text = str(elements)
        else:
            # Full page content
            raw_html = str(page.body) if hasattr(page, "body") else str(page)
            extracted_text = _html_to_clean_markdown(raw_html)

        clean_preview = extracted_text[:4000] if ai_targeted else extracted_text[:8000]

        summary = f"Scraped '{url_clean}' via Scrapling ({fetcher_used}). Extracted {len(extracted_text)} characters."
        if css_selector:
            summary += f" Matched {matched_count} item(s) for '{css_selector}'."

        return {
            "status": "success",
            "summary": summary,
            "data": {
                "url": url_clean,
                "engine": "Scrapling",
                "fetcher": fetcher_used,
                "selector": css_selector,
                "content": clean_preview,
                "total_chars": len(extracted_text)
            }
        }

    except Exception as e:
        logger.error(f"[Scrapling Error] {e}")
        # Fallback to urllib
        try:
            import urllib.request
            req = urllib.request.Request(
                url_clean,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw_html = resp.read().decode("utf-8", errors="ignore")
                clean_text = _html_to_clean_markdown(raw_html)[:4000]
                return {
                    "status": "success",
                    "summary": f"Scraped '{url_clean}' via Fallback HTTP Client ({len(clean_text)} chars).",
                    "data": {"url": url_clean, "content": clean_text, "engine": "Fallback HTTP"}
                }
        except Exception as fe:
            return {
                "status": "error",
                "summary": f"Could not scrape '{url_clean}': {e} (Fallback: {fe})",
                "data": {"error": str(e), "fallback_error": str(fe)}
            }


@tool
def crawl_website(
    start_url: str,
    max_pages: int = 3,
    css_selector: str = ""
) -> dict:
    """
    Crawls multiple pages from a website starting from a seed URL using Scrapling's link extractor.

    Args:
        start_url: The entrypoint URL to start crawling from.
        max_pages: Maximum number of linked pages to crawl (1 to 5).
        css_selector: Optional CSS selector to extract from each page.

    Returns:
        dict with crawl summary and array of scraped page records.
    """
    start_clean = start_url.strip()
    if not start_clean.startswith("http://") and not start_clean.startswith("https://"):
        start_clean = f"https://{start_clean}"

    limit = min(max(int(max_pages), 1), 5)
    logger.info(f"[Scrapling Crawl] Starting crawl from '{start_clean}' (limit={limit})")

    pages_scraped = []
    visited_urls = set()
    to_visit = [start_clean]

    try:
        from scrapling.fetchers import Fetcher

        while to_visit and len(pages_scraped) < limit:
            current_url = to_visit.pop(0)
            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)

            try:
                page = Fetcher.get(current_url, stealthy_headers=True, timeout=20)
                raw_html = str(page.body) if hasattr(page, "body") else str(page)
                
                # Extract text
                content_text = ""
                if css_selector and css_selector.strip():
                    elems = page.css(css_selector.strip())
                    if hasattr(elems, "get_all"):
                        content_text = "\n\n".join([str(x) for x in elems.get_all()[:15]])
                    elif isinstance(elems, list):
                        snippets = [str(e.text) if hasattr(e, "text") and e.text else str(e.get() if hasattr(e, "get") else e) for e in elems[:10]]
                        content_text = "\n\n".join(snippets)
                    else:
                        content_text = str(elems)
                else:
                    content_text = _html_to_clean_markdown(raw_html)

                pages_scraped.append({
                    "url": current_url,
                    "chars": len(content_text),
                    "content_preview": content_text[:800]
                })

                # Extract links for crawling next pages on same domain
                links = page.css("a::attr(href)").get_all() if hasattr(page.css("a::attr(href)"), "get_all") else []
                from urllib.parse import urljoin, urlparse
                base_domain = urlparse(start_clean).netloc

                for link in links:
                    full_link = urljoin(current_url, str(link))
                    if urlparse(full_link).netloc == base_domain and full_link not in visited_urls and full_link not in to_visit:
                        to_visit.append(full_link)

            except Exception as pe:
                logger.warning(f"[Scrapling Crawl] Error fetching {current_url}: {pe}")

        return {
            "status": "success",
            "summary": f"Scrapling crawl completed. Scraped {len(pages_scraped)} pages from '{start_clean}'.",
            "data": {
                "start_url": start_clean,
                "pages_crawled_count": len(pages_scraped),
                "pages": pages_scraped
            }
        }

    except Exception as e:
        logger.error(f"[Scrapling Crawl Error] {e}")
        return {
            "status": "error",
            "summary": f"Crawl failed for '{start_clean}': {e}",
            "data": {"error": str(e)}
        }
