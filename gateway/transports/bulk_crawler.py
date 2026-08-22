"""
🕷️ Phase 4 Transport: Asynchronous Background Bulk Crawler with SQLite Persistence (Crawlee Engine).

Executes multi-page background crawl jobs without blocking the agent loop.
Provides start_bulk_crawl(start_url) returning job_id, and get_crawl_status(job_id) for polling.
"""

import os
import re
import time
import uuid
import sqlite3
import asyncio
import threading
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
import httpx
import config
from gateway.cleaner import clean_html_to_markdown

logger = config.get_logger(__name__)

DB_PATH = os.path.join(os.getcwd(), "scratch", "crawler_jobs.db")


def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crawl_jobs (
            job_id TEXT PRIMARY KEY,
            start_url TEXT,
            status TEXT,
            pages_crawled INTEGER,
            max_pages INTEGER,
            max_depth INTEGER,
            created_at REAL,
            completed_at REAL,
            error TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crawled_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            url TEXT,
            title TEXT,
            markdown TEXT,
            content_length INTEGER,
            crawled_at REAL
        )
    """)
    conn.commit()
    return conn


def _run_background_crawl(job_id: str, start_url: str, max_depth: int, max_pages: int, domain_restricted: bool):
    """Worker function executed in background thread."""
    logger.info(f"[Bulk Crawler] Background job {job_id} started for '{start_url}' (max_pages={max_pages})")
    conn = _get_db()
    cursor = conn.cursor()

    parsed_start = urlparse(start_url)
    allowed_netloc = parsed_start.netloc

    queue = [(start_url, 0)]
    visited = set()
    pages_crawled = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }

    with httpx.Client(headers=headers, timeout=10.0, follow_redirects=True) as client:
        while queue and pages_crawled < max_pages:
            current_url, depth = queue.pop(0)
            if current_url in visited or depth > max_depth:
                continue

            visited.add(current_url)

            try:
                resp = client.get(current_url)
                if resp.status_code == 200:
                    html = resp.text
                    md = clean_html_to_markdown(html, base_url=current_url)
                    
                    # Extract page title
                    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                    title = title_match.group(1).strip() if title_match else current_url

                    cursor.execute("""
                        INSERT INTO crawled_pages (job_id, url, title, markdown, content_length, crawled_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (job_id, current_url, title, md[:10000], len(md), time.time()))
                    conn.commit()

                    pages_crawled += 1
                    cursor.execute("UPDATE crawl_jobs SET pages_crawled = ? WHERE job_id = ?", (pages_crawled, job_id))
                    conn.commit()

                    # Extract outgoing links if depth < max_depth
                    if depth < max_depth and pages_crawled < max_pages:
                        links = re.findall(r'href=[\'"]([^\'" >]+)', html)
                        for link in links:
                            full_url = urljoin(current_url, link)
                            parsed_link = urlparse(full_url)
                            if parsed_link.scheme in ["http", "https"]:
                                if not domain_restricted or parsed_link.netloc == allowed_netloc:
                                    if full_url not in visited:
                                        queue.append((full_url, depth + 1))

            except Exception as e:
                logger.warning(f"[Bulk Crawler] Error crawling {current_url}: {e}")

            time.sleep(0.2)  # Politeness delay

    cursor.execute("""
        UPDATE crawl_jobs
        SET status = 'COMPLETED', completed_at = ?
        WHERE job_id = ?
    """, (time.time(), job_id))
    conn.commit()
    conn.close()
    logger.info(f"[Bulk Crawler] Job {job_id} completed. Crawled {pages_crawled} pages.")


def start_bulk_crawl(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 10,
    domain_restricted: bool = True
) -> str:
    """
    Launches an asynchronous background web crawling job and returns immediately with a unique job ID.
    """
    job_id = f"crawl_{uuid.uuid4().hex[:8]}"
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crawl_jobs (job_id, start_url, status, pages_crawled, max_pages, max_depth, created_at, completed_at, error)
        VALUES (?, ?, 'RUNNING', 0, ?, ?, ?, NULL, NULL)
    """, (job_id, start_url, max_pages, max_depth, time.time()))
    conn.commit()
    conn.close()

    thread = threading.Thread(
        target=_run_background_crawl,
        args=(job_id, start_url, max_depth, max_pages, domain_restricted),
        daemon=True
    )
    thread.start()

    return job_id


def get_crawl_status(job_id: str) -> Dict[str, Any]:
    """
    Retrieves the status, progress, and crawled results for a bulk crawl job.
    """
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT job_id, start_url, status, pages_crawled, max_pages, created_at, completed_at, error FROM crawl_jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return {"status": "error", "error": f"Job ID '{job_id}' not found"}

    cursor.execute("SELECT url, title, content_length, markdown FROM crawled_pages WHERE job_id = ?", (job_id,))
    pages = []
    for prow in cursor.fetchall():
        pages.append({
            "url": prow[0],
            "title": prow[1],
            "content_length": prow[2],
            "snippet": prow[3][:250] + "..." if prow[3] else ""
        })

    conn.close()

    return {
        "status": "success",
        "job_id": row[0],
        "start_url": row[1],
        "job_status": row[2],
        "pages_crawled": row[3],
        "max_pages": row[4],
        "created_at": row[5],
        "completed_at": row[6],
        "pages": pages
    }
