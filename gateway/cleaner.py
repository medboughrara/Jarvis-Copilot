"""
🧹 Web Content Cleaner & HTML-to-Markdown Engine for Jarvis MCP Gateway.

Extracts core page content, eliminates navigation chrome, boilerplate, ads,
scripts, and inline CSS, producing clean LLM-ready Markdown.
"""

import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup


def clean_html_to_markdown(html_content: str, base_url: str = "") -> str:
    """
    Parses raw HTML and converts the essential body content into structured Markdown.
    Strips scripts, styles, iframes, SVGs, tracker pixels, ads, and header/footer bloat.
    """
    if not html_content or not html_content.strip():
        return ""

    try:
        import markdownify
        # First remove non-content tags with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "iframe", "object", "embed", "applet", "canvas"]):
            tag.decompose()

        for selector in [
            "[class*='cookie']", "[class*='banner']", "[class*='popup']", "[class*='advert']", "[class*='social']",
            "[id*='cookie']", "[id*='banner']", "[id*='popup']", "[id*='advert']",
            "header", "footer", "nav", "aside"
        ]:
            for el in soup.select(selector):
                try:
                    el.decompose()
                except Exception:
                    pass

        main_el = soup.find("article") or soup.find("main") or soup.find("div", {"role": "main"}) or soup.body or soup
        md = markdownify.markdownify(str(main_el), heading_style="ATX", strip=['script', 'style'])
        
        # Clean excessive newlines
        md = re.sub(r'\n{3,}', '\n\n', md).strip()
        return md

    except ImportError:
        # Resilient fallback parser
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "iframe", "object", "embed", "canvas"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        main_el = soup.find("article") or soup.find("main") or soup.body or soup

        # Convert links first
        for a in main_el.find_all("a", href=True):
            href = a["href"].strip()
            anchor_text = a.get_text().strip()
            if href and anchor_text:
                a.replace_with(f"[{anchor_text}]({href})")

        # Convert headers
        for h in main_el.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            level = int(h.name[1])
            h.replace_with(f"\n\n{'#' * level} {h.get_text().strip()}\n\n")

        # Convert list items
        for li in main_el.find_all("li"):
            li.replace_with(f"\n- {li.get_text().strip()}")

        text = main_el.get_text()
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        if title and not text.startswith("#"):
            text = f"# {title}\n\n{text}"
        return text
