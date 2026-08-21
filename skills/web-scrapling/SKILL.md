---
name: web-scrapling
description: Adaptive web scraping, crawling, and data extraction using the Scrapling framework with anti-bot bypass (Cloudflare Turnstile), stealth headless browsing, adaptive element tracking, and AI-targeted markdown sanitization.
version: "1.0.0"
metadata:
  framework: "Scrapling"
  author: "D4Vinci / Jarvis AI"
  homepage: "https://github.com/d4vinci/Scrapling"
---

# 🕷️ Web Scraping & Stealth Crawling Playbook (Scrapling)

This skill provides step-by-step guidance and architectural best practices for performing adaptive web scraping, anti-bot bypass, and structured data extraction with **Scrapling**.

---

## 🎯 When to Use Scrapling Over Basic HTTP / Fetch

| Challenge | Basic Requests / Curl | Scrapling Framework |
| :--- | :--- | :--- |
| **Cloudflare Turnstile / Challenges** | ❌ Blocked (403/503) | ✅ Auto-solved with `StealthyFetcher` |
| **TLS & Header Fingerprinting** | ❌ Easy Bot Detection | ✅ Chrome/Firefox TLS & Stealth Headers Impersonation |
| **Dynamic SPAs / React / Vue** | ❌ Empty HTML root | ✅ `DynamicFetcher` with network idle wait |
| **Website DOM / Class Changes** | ❌ Broken CSS Selectors | ✅ Adaptive similarity search (`adaptive=True`) |
| **Token Bloat for LLMs** | ❌ Massive HTML noise | ✅ `--ai-targeted` clean Markdown extraction |

---

## 🛠️ Key Scrapling Engines & Modes

### 1. Fast HTTP Scraping (`mode='fast'`)
For standard articles, news, blogs, and documentation pages:
```python
from scrapling.fetchers import Fetcher

page = Fetcher.get("https://example.com/docs", stealthy_headers=True)
content = page.css("main article").getall()
```

### 2. Stealth Anti-Bot & Cloudflare Bypass (`mode='stealth'`)
For protected sites with Cloudflare, DataDome, or Turnstile challenges:
```python
from scrapling.fetchers import StealthyFetcher

page = StealthyFetcher.fetch("https://protected-site.com", headless=True, solve_cloudflare=True)
data = page.css(".pricing-table").getall()
```

### 3. Dynamic JavaScript Rendering (`mode='dynamic'`)
For modern web apps with client-side rendering:
```python
from scrapling.fetchers import DynamicFetcher

page = DynamicFetcher.fetch("https://spa-app.com", headless=True, network_idle=True)
items = page.css(".dashboard-item").getall()
```

---

## 🔄 Adaptive Element Relocation

When scraping sites that frequently change CSS classes or DOM hierarchy:
```python
# First scrape: saves structural signature
products = page.css('.product-card', auto_save=True)

# Subsequent scrapes after website redesign:
products = page.css('.product-card', adaptive=True)
```

---

## 🤖 Jarvis Agent Tools Integration

Jarvis provides built-in tools wrapping Scrapling:
1. `scrape_web_page(url, mode='stealth', css_selector='', ai_targeted=True)`
2. `crawl_website(start_url, max_pages=3, css_selector='')`

Say to Jarvis:
- *"Scrape the latest documentation from https://example.com/api"*
- *"Extract the pricing table from https://site.com using stealth mode"*
- *"Crawl the first 3 pages of https://news.ycombinator.com"*
