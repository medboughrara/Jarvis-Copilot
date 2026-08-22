"""
🌐 Unified MCP Web Gateway Tool Surface for Jarvis Copilot.

Consolidates all web reading, anti-bot bypass, JS rendering, autonomous browsing,
and bulk crawling behind 4 clean, robust tools:
1. get_web_content(url)
2. browse_web_page(task_instruction, start_url)
3. start_bulk_crawl(start_url, max_depth, max_pages)
4. get_crawl_status(job_id)
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool
import config
from gateway.escalation_engine import fetch_web_content_escalated
from gateway.transports.browser_agent import execute_browser_task
from gateway.transports.bulk_crawler import (
    start_bulk_crawl as run_start_bulk_crawl,
    get_crawl_status as run_get_crawl_status
)

logger = config.get_logger(__name__)


def _run_async(coro):
    """Safely runs async coroutine within sync tool execution context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        return loop.run_until_complete(coro)
    except RuntimeError:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        res = new_loop.run_until_complete(coro)
        new_loop.close()
        return res


@tool
def get_web_content(
    url: str,
    force_method: str = "",
    bypass_cache: bool = False
) -> dict:
    """
    Fetches clean, LLM-ready Markdown from any URL or web domain.
    Automatically escalates through Direct Fetch -> Anti-Bot TLS Impersonation -> Dynamic JS Render -> Browser Agent.

    Args:
        url: The website URL to read (e.g. 'https://en.wikipedia.org/wiki/Printed_circuit_board', 'https://github.com').
        force_method: Optional manual override: 'direct_fetch', 'antibot_curl_cffi', 'crawl4ai_render', 'browser_agent'.
        bypass_cache: Set to True to bypass cached content.

    Returns:
        dict containing clean Markdown, resolved escalation tier, status, and latency.
    """
    clean_url = url.strip()
    logger.info(f"[MCP Gateway Tool] get_web_content called for: '{clean_url}'")
    
    res = _run_async(fetch_web_content_escalated(clean_url, force_method=force_method or None, bypass_cache=bypass_cache))
    
    if res.get("status") == "success":
        resolved_by = res.get("resolved_by", "direct_fetch")
        summary = f"Successfully fetched '{clean_url}' via [{resolved_by}] in {res.get('latency_ms', 0)}ms ({res.get('content_length', 0)} characters)."
    else:
        summary = f"Failed to fetch '{clean_url}': {res.get('error', 'Unknown error')}."

    return {
        "status": res.get("status", "error"),
        "summary": summary,
        "data": res
    }


@tool
def browse_web_page(
    task_instruction: str,
    start_url: str = "",
    max_steps: int = 5
) -> dict:
    """
    Executes an autonomous multi-step interactive browsing mission (search, form filling, pricing lookup, pagination).

    Args:
        task_instruction: Natural language mission (e.g. 'Find unit price and stock for STM32F405 on LCSC').
        start_url: Optional initial URL to start navigation from.
        max_steps: Maximum interactive actions.

    Returns:
        dict containing synthesized findings, visited URLs, and action log.
    """
    logger.info(f"[MCP Gateway Tool] browse_web_page called: '{task_instruction}'")
    res = _run_async(execute_browser_task(task_instruction, start_url=start_url, max_steps=max_steps))
    
    if res.get("success"):
        summary = f"Browser Agent completed task: '{task_instruction[:60]}...' Outcome: {res.get('result', '')[:120]}..."
    else:
        summary = f"Browser Agent failed task '{task_instruction}': {res.get('error', 'Unknown')}"

    return {
        "status": "success" if res.get("success") else "error",
        "summary": summary,
        "data": res
    }


@tool
def start_bulk_crawl(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 10,
    domain_restricted: bool = True
) -> dict:
    """
    Launches an asynchronous background bulk crawl and returns immediately with a job ID.
    Non-blocking: does not halt agent execution.

    Args:
        start_url: Root URL to begin crawling.
        max_depth: Link traversal depth limit (default 2).
        max_pages: Maximum pages to crawl (default 10).
        domain_restricted: If True, stays within same domain.

    Returns:
        dict containing job_id and status.
    """
    logger.info(f"[MCP Gateway Tool] start_bulk_crawl called for: '{start_url}'")
    job_id = run_start_bulk_crawl(start_url, max_depth=max_depth, max_pages=max_pages, domain_restricted=domain_restricted)
    
    return {
        "status": "success",
        "summary": f"Background bulk crawl initiated for '{start_url}'. Job ID: **{job_id}**.",
        "data": {
            "job_id": job_id,
            "start_url": start_url,
            "max_pages": max_pages,
            "max_depth": max_depth
        }
    }


@tool
def get_crawl_status(job_id: str) -> dict:
    """
    Polls the progress and retrieves crawled page markdowns for a background bulk crawl job.

    Args:
        job_id: The job ID returned by start_bulk_crawl.

    Returns:
        dict with job status (RUNNING | COMPLETED), pages crawled, and list of page summaries.
    """
    logger.info(f"[MCP Gateway Tool] get_crawl_status called for: '{job_id}'")
    res = run_get_crawl_status(job_id)
    
    if res.get("status") == "success":
        summary = f"Crawl Job [{job_id}]: Status [{res.get('job_status')}] — {res.get('pages_crawled', 0)}/{res.get('max_pages', 0)} pages crawled."
    else:
        summary = f"Crawl Job [{job_id}] error: {res.get('error')}"

    return {
        "status": res.get("status", "error"),
        "summary": summary,
        "data": res
    }
