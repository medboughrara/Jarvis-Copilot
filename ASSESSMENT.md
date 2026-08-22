# Phase 0 Assessment: Jarvis Local MCP Web Gateway App

## 1. Orchestration Analysis
- **Framework**: Jarvis utilizes a hybrid architecture built on top of LangChain / LangGraph, standard `StructuredTool` definitions, and a native Model Context Protocol (MCP) server.
- **MCP Compatibility**: Jarvis already runs a native stdio MCP server (`mcp_server.py`) using the official standard `mcp.server.MCPServer` protocol, exposing 61 registered tools dynamically.
- **Gateway Integration Strategy**: The new Web Gateway will provide a unified, local-first tool surface (`get_web_content`, `start_bulk_crawl`, `get_crawl_status`, `execute_browser_task`) that consolidates direct fetch, `curl_cffi` anti-bot fallback, `Crawl4AI` clean markdown rendering, and `browser-use` autonomous multi-step navigation behind an internal escalation engine.

## 2. LLM Backend Analysis
- **Current Setup**: API-based multi-tier rotation pool:
  - **Google Gemini API**: 5 active keys rotating across `gemini-3.6-flash` and `gemini-2.5-flash`.
  - **NVIDIA NIM Cloud**: Reasoning models (`deepseek-ai/deepseek-r1`, `meta/llama-3.3-70b-instruct`) and `nemotron` vision/embeddings.
  - **Composio API**: 5 connected apps (Gmail, Calendar, Notion, Sheets, Docs).
- **Configuration for Gateway & Browser Agent**:
  - `browser-use` and `Crawl4AI` will be bound directly to the existing Gemini LLM backend (`ChatGoogleGenerativeAI(model="gemini-2.5-flash")` or `gemini-3.6-flash`), eliminating external cloud or heavy local GPU requirements while preserving full vision & DOM parsing capabilities.

## 3. Environment & Runtime
- **Operating System**: Windows 11 AMD64
- **Python Version**: Python 3.12.10 (virtual environment at `.venv`) / Python 3.9.13 (system)
- **Node.js Version**: v23.7.0
- **Docker Status**: Docker CLI v29.1.3 is installed, but Docker Desktop daemon is currently stopped / not running on Windows named pipe (`//./pipe/dockerDesktopLinuxEngine`).
  - *Implication*: Crawl4AI and browser automation will run via direct local Python execution (`crawl4ai` + `playwright` / `scrapling` / `curl_cffi`) with zero dependency on Docker daemon state.
- **Anti-Bot & Automation Stack**: `curl_cffi` (v0.13.0) installed and verified; `playwright` (v1.60.0), `scrapling` (v0.2.99), `primp`, `httpx` (v0.28.1), and `aiohttp` (v3.13.5) present.

## 4. Existing Web Capabilities in Jarvis
- **Existing Tools**:
  1. `tools/scrapling_tool.py`: `scrape_web_page`, `crawl_website` (using Scrapling / Playwright).
  2. `tools/reach_tool.py`: Multi-engine web search with `primp` and DuckDuckGo/Yahoo/Yandex fallbacks.
  3. `tools/datasheet_rag_tool.py`: Web PDF datasheet fetcher.
  4. `tools/composio_tool.py`: Composio third-party web actions.
- **Gateway Role**: The MCP Web Gateway will consolidate and replace fragmented scraping/fetching routines with a single, intelligent escalation tool surface:
  1. **Direct Fast Fetch** (HTTPX / Aiohttp with clean HTML-to-Markdown parsing)
  2. **Anti-Bot Transport** (`curl_cffi` browser TLS/JA3 impersonation)
  3. **Full JS-Rendering & Markdown Extraction** (`Crawl4AI` / Scrapling Playwright engine)
  4. **Autonomous Interactive Browser Agent** (`browser-use` with Gemini vision)

## 5. Existing Registered MCP Servers & Tools
- `Jarvis-PCB-Copilot` (`mcp_server.py`): 61 active MCP tools covering KiCad EDA, thermal loss, signal integrity, autorouting, manufacturing exports, preferred parts, and Composio workspace tools.
- *Avoid Duplication*: The new Web Gateway will cleanly register 3–4 unified gateway tools without polluting the agent with individual competing scraper libraries.

## 6. Verification of Source Repositories

| Project | License | Status & Last Activity | Role in Architecture |
| :--- | :---: | :---: | :--- |
| **Crawl4AI** (`unclecode/crawl4ai`) | Apache 2.0 | Highly Active (v0.9.x released July 2026) | **Phase 1**: Primary local JS-heavy crawler producing clean LLM-ready markdown |
| **browser-use** (`browser-use/browser-use`) | MIT | Highly Active (Browser Harness 3.0) | **Phase 2**: Autonomous interactive multi-step browser agent |
| **curl_cffi** (`lexiforest/curl_cffi` / `lwthiker/curl-impersonate`) | MIT | Active (v0.13.0 installed) | **Phase 3**: Anti-bot fallback transport with TLS JA3/JA4 browser impersonation |
| **Crawlee** (`apify/crawlee`) | Apache 2.0 | Active (Apify Python release) | **Phase 4**: Background asynchronous bulk crawler with SQLite job store |
| **Scrapy** (`scrapy/scrapy`) | BSD 3-Clause | Mature / Active | Fallback option if custom crawler middleware needed |
| **Firecrawl** (`firecrawl/firecrawl`) | AGPL 3.0 | Cloud-first (requires Redis + Celery) | **Out of Scope** (heavy infra not suited for pure local MCP) |
| **AutoScraper** (`alirezamika/autoscraper`) | MIT | Lightly maintained | **Out of Scope** (niche rule learner) |
| **awesome-mcp-servers** | Reference | Active | Checked for existing servers to avoid custom code duplication |
| **public-apis** | Reference | Active | Checked before scraping to prioritize free stable REST APIs |

## 7. Starting Phase & Blockers Found
- **Starting Phase**: Proceed immediately to **Phase 1 (Primary Content Fetch: Crawl4AI / Local Markdown Engine)**.
- **Blockers**: None. Docker daemon is inactive, so all components will run natively in Python via `playwright`, `curl_cffi`, and async Python runtime with zero external infrastructure overhead.
