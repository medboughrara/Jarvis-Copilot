"""
⚡ Level 3 Transport: Crawl4AI & Playwright Stealth Dynamic JS Render for Jarvis MCP Gateway (Phase 1).

Executes JavaScript, waits for dynamic DOM hydration, and extracts clean, LLM-ready Markdown
from complex single-page apps (SPAs) and interactive web applications.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import config
from gateway.cleaner import clean_html_to_markdown

logger = config.get_logger(__name__)


async def crawl4ai_fetch(url: str, wait_for_selector: Optional[str] = None, timeout_seconds: float = 25.0) -> Dict[str, Any]:
    """
    Renders dynamic web pages via Crawl4AI / Playwright Stealth engine and returns clean Markdown.
    """
    logger.info(f"[Crawl4AI Transport] Rendering dynamic page: '{url}'")

    # 1. Try native Crawl4AI async web crawler if installed
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        config_obj = CrawlerRunConfig(
            word_count_threshold=10,
            excluded_tags=['nav', 'footer', 'header', 'script', 'style'],
            remove_overlay_elements=True
        )
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url, config=config_obj)
            if result.success and result.markdown:
                return {
                    "success": True,
                    "status_code": 200,
                    "url": url,
                    "markdown": result.markdown.raw_markdown if hasattr(result.markdown, 'raw_markdown') else str(result.markdown),
                    "content_length": len(str(result.markdown)),
                    "transport": "crawl4ai_render"
                }
    except ImportError:
        pass
    except Exception as ce:
        logger.warning(f"[Crawl4AI Transport] Crawl4ai native execution notice: {ce}")

    # 2. Resilient Fallback: Playwright / Scrapling Stealth Dynamic Engine
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = None
            for channel in ["msedge", "chrome", None]:
                try:
                    kwargs = {"headless": True, "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled"]}
                    if channel:
                        kwargs["channel"] = channel
                    browser = await p.chromium.launch(**kwargs)
                    break
                except Exception:
                    continue

            if not browser:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            
            # Navigate and wait for DOM content load
            await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=5000)
                except Exception:
                    pass
            else:
                await asyncio.sleep(1.5)  # Allow JS scripts to render

            html = await page.content()
            await browser.close()

            markdown = clean_html_to_markdown(html, base_url=url)
            return {
                "success": True,
                "status_code": 200,
                "url": url,
                "markdown": markdown,
                "content_length": len(markdown),
                "transport": "crawl4ai_playwright_render"
            }

    except Exception as pe:
        logger.error(f"[Crawl4AI Transport] Playwright render error on '{url}': {pe}")
        return {
            "success": False,
            "status_code": 0,
            "error": str(pe),
            "requires_browser_agent": True
        }
