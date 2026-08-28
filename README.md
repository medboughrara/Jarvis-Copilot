# 🤖 Jarvis AI — Universal General-Purpose Assistant & Autonomous Copilot

A local, voice-activated "Jarvis-style" open-source AI super-assistant designed for **general personal productivity, daily work automations, hierarchical memory trees (Karpathy Knowledgebase), Goals & Tasks Kanban boards, TokenJuice token compression, visual trigger workflows (Tinyflows), universal 17-channel messaging (Telegram, Discord, Slack, WhatsApp, Gmail), desktop app control, visual screen analysis, PDF document RAG, Graphify & Obsidian Knowledge Graphs, MemPalace Long-Term Memory, and specialized hardware/electronics engineering (3D procedural modeling, KiCad EDA, IPC-2221 thermal & autorouting)**.

<div align="center">

### 🎬 Live System Demo & Tactical HUD Walkthrough

![Live System Demo & Tactical HUD Walkthrough](demo.gif)

![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg?style=for-the-badge&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/Orchestration-LangChain-purple.svg?style=for-the-badge&logo=chainlink&logoColor=white)
![OpenHuman](https://img.shields.io/badge/Harness-OpenHuman_Architecture-FF6B6B.svg?style=for-the-badge)
![TokenJuice](https://img.shields.io/badge/Compression-TokenJuice_-68%25-00F2FF.svg?style=for-the-badge)
![Tinyflows](https://img.shields.io/badge/Automations-Tinyflows_Engine-10B981.svg?style=for-the-badge)
![Obsidian](https://img.shields.io/badge/Vault-Obsidian_Graph-7C3AED.svg?style=for-the-badge&logo=obsidian&logoColor=white)
![MemPalace](https://img.shields.io/badge/Memory-MemPalace_Loci-00D2FF.svg?style=for-the-badge)
![Composio MCP](https://img.shields.io/badge/Cloud_Apps-Composio_1000+-6C5CE7.svg?style=for-the-badge)
![FastMCP](https://img.shields.io/badge/Tools-89+_Active_Tools-FF4B4B.svg?style=for-the-badge)

</div>

---

> [!NOTE]
> **Universal Open-Source Personal Assistant**: Jarvis AI combines hands-free voice control, interactive animated mascot reactions, hierarchical scored memory trees, goals kanban boards, trigger-driven workflows, multi-channel messaging (Telegram/Discord/WhatsApp/Slack/Gmail), desktop app automation, long-term spatial memory, interactive Obsidian knowledge graphs, procedural 3D electronic part generation, and automated KiCad PCB engineering across **89+ registered tools**.

---

## 🏛️ Universal System Architecture & Execution Pipeline

```mermaid
graph TD
    subgraph IN ["Multimodal Input Layer"]
        MIC["🎙️ Hands-Free Mic / Voice PTT"] --> STT["⚡ Faster-Whisper / WebSpeech STT"]
        UI["🖥️ Next-Gen Glassmorphic Assistant UI"] --> CMD["💬 REST API / Web Server"]
        SCR["👁️ Active Screen Capture"] --> OCR["📸 OmniParser V2 & Nemotron OCR"]
    end
    
    subgraph ORCH ["Split-Brain Harness & Orchestration Engine"]
        STT --> MED["⚡ Split-Brain Medulla (Reflex Triage in <5ms)"]
        CMD --> MED
        OCR --> MED
        MED --> AGENT["🧠 JarvisAgent (89+ Active Tools)"]
        AGENT --> SEC["🛡️ AgentShield Security & Approval Gates"]
        AGENT --> MEM_TREE["🌳 Scored Hierarchical Memory Tree"]
        AGENT --> MEM_PALACE["🏰 MemPalace Verbatim Long-Term Memory"]
        AGENT --> FLOWS["⚙️ Tinyflows Trigger Automation Engine"]
        AGENT --> TJ["🧃 TokenJuice Compression Engine (up to 80% savings)"]
    end
    
    subgraph BRAIN ["Multi-Tier LLM Engine Pool"]
        AGENT --> T1["⚡ Tier 1: Gemini 2.5 / 3.6 Flash Multi-Key Pool"]
        T1 -.->|Fallback| T2["🌌 Tier 2: NVIDIA NIM Cloud - Kimi 2.6 / Nemotron 3"]
        T2 -.->|Fallback| T3["☁️ Tier 3: Ollama Cloud - GLM-5.2 / Kimi-K3"]
        T3 -.->|Fallback| T4["💻 Tier 4: Local RTX 3050 Llama3:8b"]
    end
    
    subgraph SUITE ["Universal Capability Tools (89+ Tools)"]
        AGENT --> CHANNELS["📡 Multi-Channel Hub (Telegram / Discord / Slack / WhatsApp / Gmail)"]
        AGENT --> WORKSPACE["💼 Google Sheets / Notion / Calendar / Docs / Drive"]
        AGENT --> KANBAN["📋 Goals & Todos Kanban Manager"]
        AGENT --> CRAWLER["🌐 Crawl4AI & Scrapling Deep Web Search"]
        AGENT --> HARDWARE["📐 KiCad 8/9 EDA / DRC / Thermal / 3D img2obj Mesher"]
    end
    
    subgraph OUT ["Multimodal Output Layer"]
        AGENT --> TTS["🔊 Kokoro 24kHz Neural TTS / NVIDIA Magpie"]
        TTS --> SPK["📣 Speaker Playback & Audio Uplink"]
        AGENT --> WEBGL["🌊 Interactive Circle Edge Voice Wave Shader"]
        AGENT --> HUD_LOG["💻 Live Web HUD Terminal Log Stream & 3D WebGL Canvas"]
    end
```

---

## 🖥️ Next-Gen Conversational & General-Purpose UI Showcase

<div align="center">

### 💬 1. Assistant Chat with Rich GitHub Markdown & Live Tool Execution
*Streaming conversational interface with full Markdown formatting (headings, bold accents, bullet points, syntax-highlighted code blocks), live tool telemetry execution, and single-voice high-fidelity neural audio streaming.*

![Assistant Chat Interface](docs/images/01_assistant_chat.png)

---

### 🎙️ 2. Conversational Avatar Mode (Real-Time Voice, 3D Mascot & Reflected Aura)
*Full-duplex voice conversation with an expressive animated 3D holographic mascot, cursor-tracking pupils, dynamic mouth viseme lip-sync, real-time waveform audio equalizers, customizable atmospheric reflected aura lighting, and hands-free auto-listening.*

![Conversational Avatar Mode](docs/images/02_conversational_avatar.png)

---

### 🧠 3. Hierarchical Scored Memory Tree & Goals Kanban Board
*4-Column Goals Kanban manager (`To Do`, `In Progress`, `Blocked`, `Done`) and hierarchical memory nodes with importance scoring (1–10) mirrored into Obsidian Vault.*

![Hierarchical Memory Tree & Goals Kanban](docs/images/03_intelligence_memory.png)

---

### ⚙️ 4. Automated Workflows & Routines Studio (Tinyflows Engine)
*Trigger-driven automation graph with pre-built routines (Daily Executive Briefings, Autonomous Web Research, Sponsor Outreach pipelines, PCB DRC Audits) and one-click execution.*

![Automated Workflows Studio](docs/images/04_workflows.png)

---

### 📡 5. Universal Multi-Channel Communications Gateway
*Unified hub monitoring connected accounts (Gmail, Discord, Telegram, Slack, WhatsApp, Notion, Google Sheets) with quick outbound multi-channel message dispatcher.*

![Multi-Channel Communications Gateway](docs/images/05_channels_hub.png)

---

### 📱 6. Universal 12-App Recipes & Autonomous Cron Daemon (OpenHuman Subsystems)
*One-click multi-platform automation recipes (Gmail, Outlook, LinkedIn, Slack, Telegram, Discord, Twitter/X, Instagram, WhatsApp, Google Meet, Zoom, BrowserScan), autonomous background scheduled heartbeat daemon, and interactive Python/Math Sandboxed Code Runner.*

![Universal 12-App Recipes](docs/images/06_recipes_cron_top.png)

![Autonomous Cron Daemon & Python Sandbox](docs/images/06_recipes_cron_bottom.png)

---

### 📐 7. KiCad PCB Hardware & 3D Modeling Suite
*Schematic AST S-expression inspector, DRC/ERC rules checker, Joule thermal loss simulator, signal integrity estimator, and procedural 3D electronic part generator.*

![KiCad PCB Hardware Suite](docs/images/07_pcb_hardware.png)

</div>

---

## 🧠 Obsidian Knowledge Graph & Visual Canvas

Jarvis uses **Graphify-Labs** AST extraction and semantic clustering to transform all codebase symbols, schematic nets, and architectural tools into an interactive **Obsidian Knowledge Graph Vault**:

<div align="center">

### 🌐 Global Force-Directed Knowledge Graph (850 Nodes & 1,654 Edges)

![Obsidian Global Knowledge Graph View](docs/images/obsidian_graph_view.png)

### 📋 Infinite Visual Whiteboard (`Architecture_Graph.canvas`)

![Obsidian Visual Whiteboard Canvas](docs/images/obsidian_canvas_whiteboard.png)

</div>

* **Interactive Force Physics**: Color-coded clusters for KiCad EDA, Agent Orchestration, Web Gateway, Composio Workspace, and 3D Modeling.
* **911 Bi-directional Notes**: Every function, tool, and class has its own Markdown note with `[[wikilinks]]` and caller graphs.
* **Agent Wiki**: 61 cross-linked community articles providing high-level subsystem overviews.

---

## ⚡ Hardware Constraints & Local/Cloud Resource Distribution

Optimized to run seamlessly on a standard Windows laptop with an **Intel Core i5 CPU**, **24GB RAM**, and an **NVIDIA RTX 3050 GPU (6GB VRAM)**:

| Subsystem | Target Processor | Model / Framework | Optimization |
| :--- | :--- | :--- | :--- |
| **Wake Word Engine** | CPU | `openWakeWord` ("jarvis") | ONNX Runtime (CPU) |
| **Speech-to-Text (STT)** | CPU / Cloud | `Faster-Whisper` (`base.en`) / `NVIDIA Whisper v3` | `INT8` Quantization + Cloud API Fallback |
| **Text-to-Speech (TTS)** | CPU / Cloud | `Kokoro-82M` (24kHz) / `NVIDIA Magpie TTS` | ONNX Runtime + Cloud Neural Voice |
| **WebGL Voice Visualizer**| Web Browser | Custom GLSL Fragment Shader | Dynamic Standing Audio Wave on Arc Reactor Edge |
| **Orchestration & Harness** | CPU | LangChain + ECC Agent Harness | Reflex Rules + AgentShield + Context Compression |
| **LLM Tier 1 (Cloud Pool)** | Cloud Pool | `Google Gemini 3.6 Flash` (5 API Keys) | Round-Robin Rotation + 429 Rate Limit Cooling |
| **LLM Tier 2 (Cloud Pool)** | Cloud Pool | `Moonshot Kimi 2.6` & `NVIDIA Nemotron 3` | Deep Hardware & Logical Reasoning via NVIDIA NIM |
| **LLM Tier 3 (Cloud Pool)** | Cloud Pool | `Ollama Cloud` (`glm-5.2:cloud`, `kimi-k3:cloud`) | Secondary Cloud Fallback |
| **LLM Tier 4 (Local GPU)** | GPU RTX 3050 | `Llama 3 8B` (`ChatOllama`) | Zero-Downtime Offline Fallback |
| **Long-Term Memory Engine** | CPU / Local | `MemPalace` (`all-MiniLM-L6-v2` ONNX) | Zero-Loss Verbatim Loci Hierarchy & Temporal Graph |
| **Knowledge Graph Engine** | CPU / Local | `Graphify` + AST Parsers | Obsidian Vault with Canvas, Wiki & Hub Labels |
| **3D Modeling Engine** | CPU / Browser | `img2obj` Procedural Builder + Three.js | Wavefront .OBJ/.MTL & WebGL Parametric Shaders |
| **Web Gateway Escalation** | CPU / Local | `curl_cffi` + `Crawl4AI` + Playwright | 4-Tier Anti-Bot & Autonomous Agent Fallback |
| **App & Cloud Integrations**| Cloud / HTTP | Composio MCP Apps (1000+ Services) | **Discord**, Gmail, Calendar, Notion, Sheets, Docs |

---

## 🛠️ Complete Capabilities Matrix (89+ Active Tools)

| # | Capability Domain | Subsystem / Module | Key Functions & Features |
| :--- | :--- | :--- | :--- |
| **1** | **🎙️ Conversational Avatar Voice Mode**| `ui/index.html` & `voice/` | Interactive animated holographic mascot with reactive eyes, dynamic viseme mouth lip-sync, live audio visualizer, subtitles, and hands-free continuous loop. |
| **2** | **📝 Rich Markdown & Speech Replay**| `ui/app.js` & `ui/index.html` | Full GitHub-flavored Markdown rendering (headings, tables, syntax-highlighted code blocks) with interactive `🔊 Replay` audio synthesis button on every bubble. |
| **3** | **🌳 Hierarchical Scored Memory Tree**| `tools/memory_tree_tool.py` | Scored memory tree in SQLite (`/projects`, `/people`, `/research`, `/preferences`) with 1–10 importance weighting and instant Obsidian Vault note mirroring. |
| **4** | **📋 Goals & Tasks Kanban Manager**| `tools/memory_tree_tool.py` | 4-column kanban board (`To Do`, `In Progress`, `Blocked`, `Done`) with progress bars, priority weights (`urgent`, `high`, `medium`), and deadlines. |
| **5** | **🧃 TokenJuice Compression Engine**| `tools/tokenjuice_tool.py` | Semantic JSON, AST signature, and log compression reducing LLM context token usage by 40% to 80%. |
| **6** | **⚙️ Trigger-Driven Tinyflows Engine**| `tools/workflows_engine_tool.py` | Durable trigger-driven workflow engine (cron, webhook, channel message, manual) with execution logs and approval gates. |
| **7** | **📡 Universal Multi-Channel Gateway**| `tools/multichannel_hub_tool.py` | Unified outbound dispatcher and status monitor for Telegram, Discord, Slack, WhatsApp, and native Gmail/SMTP email. |
| **8** | **⚡ Split-Brain Medulla Reflex Engine**| `agent/medulla_reflex.py` | Sub-5ms intent triage separating instant reflex rules, memory queries, and deep multi-step reasoning with human approval gates. |
| **9** | **🧠 Graphify + Obsidian Vault** | `tools/obsidian_knowledge_graph_tool.py` | Extracts AST code relationships and semantic clusters into a complete Obsidian Vault (911 linked notes, `Architecture_Graph.canvas`, `Interactive_Graph.html`, Agent Wiki, and custom subsystem color filters). |
| **10**| **🏰 MemPalace Long-Term Memory** | `tools/mempalace_tool.py` | 100% Local-first verbatim memory using the spatial Method of Loci (`Wings -> Rooms -> Halls -> Drawers`), temporal SQLite entity graph, and fast L0/L1 wake-up briefing (~800 tokens). |
| **11**| **📐 img2obj 3D Component Modeler**| `tools/img2obj_component_3d_tool.py` | Procedurally generates Wavefront `.obj`/`.mtl` and Three.js 3D models for electronic packages (0402, 0603, 0805, SOT-223, SOIC-8, TSSOP-28, QFP-48, QFN-32, TO-220, USB-C) and links them to `.kicad_pcb` footprints. |
| **12**| **🌐 Local MCP Web Gateway** | `gateway/` | 4-Tier escalation ladder: Tier 1 Direct HTTP $\to$ Tier 2 `curl_cffi` TLS/JA3 $\to$ Tier 3 Crawl4AI/Playwright JS $\to$ Tier 4 Autonomous Vision Browser Agent. |
| **13**| **💬 Discord Integration** | `tools/composio_apps_tool.py` | Direct **Discord** integration: send channel messages, fetch channel message history, and create new channels (`DISCORDBOT`). |
| **14**| **💻 Desktop & System Control** | `tools/system_control_tool.py` | Time/date & greetings, launch local apps (Notepad, Calculator, VS Code, Explorer), open URLs/websites, take screenshots, tell jokes, and log voice notes. |
| **15**| **📬 Workspace App Automation** | `tools/composio_apps_tool.py` | Full Composio integration for **Gmail** (fetch, send, search, drafts), **Google Calendar**, **Notion**, **Google Docs**, and **Google Sheets**. |
| **16**| **🧠 Multi-Tier LLM Brain Pool** | `agent/copilot.py` & `agent/key_manager.py` | 4-Tier Fallback: Tier 1 Gemini 2.5/3.6 Flash Pool -> Tier 2 NVIDIA NIM Cloud -> Tier 3 Ollama Cloud -> Tier 4 Local GPU `llama3:8b`. |
| **17**| **⚡ ECC Agent Harness Engine** | `agent/instincts.py`, `agent/security.py`, `agent/context_compressor.py` | Automatic hardware & work reflex rules, AgentShield workspace security guard, and incremental conversation history compressor. |
| **18**| **🗂️ Preferred Parts & Circuit Templates**| `tools/preferred_parts_tool.py` & `tools/circuit_templates_tool.py` | Component library memory & parametric circuit generators (LDO regulators, buck converters, voltage dividers, BME280 sensor breakout). |
| **19**| **🔁 Self-Correcting ERC/DRC Loop**| `agent/verify_loop.py` | Autonomous Agentic Verification Loop executing KiCad ERC/DRC, catching design violations, and auto-correcting schematic nets. |
| **20**| **🛤️ 2-Layer Grid Autorouter** | `tools/autorouter_tool.py` | Automated multi-layer grid autorouter with 45-degree trace routing and DFM rule verification. |
| **21**| **🏭 Turnkey Manufacturing Exporter**| `tools/manufacturing_tool.py` | Automated fabrication export: RS-274X Gerbers, Excellon NC Drills, Pick-and-Place (CPL), BOM CSV, and JLCPCB cost estimation. |
| **22**| **👁️ OmniParser Screen Vision** | `tools/omniparser_tool.py` | Active screen capture layout parsing with `RapidOCR` ONNX engine to inspect UI elements, component dialogs, and code editors. |
| **23**| **📚 Local PDF & Datasheet RAG** | `tools/datasheet_rag_tool.py` | Local document & datasheet RAG powered by **NVIDIA Nemotron 3 Embed 1B** and ChromaDB vector store. |
| **24**| **🌐 Live Web Search & Compliance** | `tools/reach_tool.py` | Live web search for technical datasheets, general information, and regulatory compliance (RoHS 3 / FCC Part 15). |
| **25**| **🎫 GitHub Issue & Repo Manager** | `tools/github_tool.py` | Log bugs, task reminders, or audit findings directly as labeled GitHub issues. |
| **26**| **📄 Engineering & General Doc Exporter**| `tools/doc_exporter_tool.py` | Formats and exports audit reports, meeting notes, or general document summaries to `docs/` and `scratch/` as Markdown/JSON. |
| **27**| **🎨 NVIDIA FLUX.1 Image Generator** | `tools/nvidia_nim_tool.py` | Text-to-Image generation for diagrams, UI concepts, and visuals via `black-forest-labs/flux.1-schnell`. |
| **28**| **🧩 Baidu Unlimited-OCR Long Parser** | `tools/unlimited_ocr_tool.py` | Long-horizon document parsing into structured Markdown using Baidu Reference Sliding Window Attention (`baidu/Unlimited-OCR`). |
| **29**| **📐 KiCad EDA & Circuit Parser** | `tools/kicad_tool.py` & `tools/kicad_editor.py` | Direct KiCad `.kicad_sch` & `.kicad_pcb` S-expression AST manipulation and net wiring. |
| **30**| **🔥 IPC-2221 Thermal Trace Solver** | `tools/thermal_tool.py` | Calculates trace widths, copper $I^2R$ power loss, and junction temperature rise for voltage regulators ($T_j = T_a + P_d \cdot R_{\theta JA}$). |
| **31**| **⚡ Signal Integrity Bounds Solver** | `tools/signal_integrity_tool.py` | Calculates I2C pullup bounds ($R_{\min} / R_{\max}$), UART series damping resistors, and CAN bus split termination ($120\Omega$). |
| **32**| **📦 Supply Chain & Risk Tracker** | `tools/supply_chain_tool.py` | Evaluates component lifecycle (Active/NRND/EOL), distributor stock availability, and JLCPCB basic/extended part risk. |
| **33**| **🔌 Stdio FastMCP Server (89+ Tools)** | `mcp_server.py` | Automatically exposes all 89+ Jarvis tools over stdio Model Context Protocol for direct integration into Claude Code, Cursor, Windsurf, and VS Code. |

---

## 🏗️ Project Architecture & Directory Layout

```
d:/aaaassistan_pcb/
├── config.py                 # Pydantic Settings & logger configuration
├── main.py                   # Async main execution loop (Wake Word -> STT -> LLM -> TTS)
├── mcp_server.py             # FastMCP Stdio MCP server exposing 89+ dynamic tools
├── web_server.py             # Cyberpunk Tactical HUD REST API & static server
├── test_capabilities.py      # System capability verification suite
├── requirements.txt          # PyTorch CUDA 12.1, LangChain, MemPalace & MCP dependencies
├── README.md                 # Project documentation & capability matrix
├── DISCORD_SETUP.md          # Setup guide for Discord Composio integration
├── demo.gif                  # Native GitHub animated video demo
├── ui/                       # Next-Gen Glassmorphic Conversational HUD Web Interface
│   ├── index.html            # Web HUD with Markdown rendering & Conversational Avatar Mode
│   ├── app.js                # App logic, Web Speech synthesis, & Avatar state controller
│   └── tiny_mascot.riv       # Rive native vector mascot asset
├── gateway/                  # Local MCP Web Gateway (4-Tier Escalation Architecture)
│   ├── escalation_engine.py  # Transparent routing (Direct -> curl_cffi -> Crawl4AI -> Agent)
│   ├── cleaner.py            # Resilient HTML-to-Markdown cleaner
│   ├── cache_and_politeness.py # In-memory TTL cache & domain throttling
│   ├── mcp_gateway_tool.py   # Gateway MCP tools (get_web_content, browse_web_page, etc.)
│   └── transports/           # Direct, Antibot (curl_cffi), Crawl4AI, Browser Agent, Bulk Crawler
├── obsidian_vault/           # Graphify-Generated Obsidian Knowledge Graph Vault
│   ├── .obsidian/graph.json  # Subsystem color groupings and physics settings
│   ├── Architecture_Graph.canvas # Obsidian Infinite Visual Whiteboard
│   ├── Interactive_Graph.html# Standalone D3/WebGL interactive graph viewer
│   ├── Memory_Tree/          # Mirrored Scored Memory Tree notes
│   ├── Wiki/                 # Cross-referenced Agent Wiki articles
│   └── ... (911 interconnected [[wikilink]] Markdown notes)
├── voice/
│   ├── wakeword.py           # openWakeWord CPU ONNX background listener
│   ├── stt.py                # Faster-Whisper STT + NVIDIA Whisper Large v3
│   └── tts.py                # Kokoro-82M 24kHz TTS + NVIDIA Magpie TTS
├── agent/
│   ├── copilot.py            # LangChain JarvisAgent with 89+ active tools & multi-tier LLM pool
│   ├── medulla_reflex.py     # Split-Brain fast reflex triage & attention queue
│   ├── session_context.py    # JarvisSessionContext per-session model container
│   ├── key_manager.py        # Multi-key Gemini rotation & real-time metrics manager
│   ├── composio_router.py    # Dynamic tool router & context optimizer
│   ├── verify_loop.py        # Self-correcting ERC/DRC agentic verify loop
│   ├── instincts.py          # Automatic hardware & work reflex rules (ECC-inspired)
│   ├── security.py           # AgentShield workspace path & argument security guard
│   ├── context_compressor.py # Incremental token budget & history compressor
│   ├── workflows.py          # Autonomous multi-stage audit workflows
│   └── prompts.py            # System prompt persona configuration
├── skills/                   # AAS & Claude-style SKILL.md playbooks
├── tools/
│   ├── memory_tree_tool.py   # Hierarchical memory tree, Goals Kanban, People dossiers & Obsidian mirror
│   ├── tokenjuice_tool.py    # TokenJuice semantic JSON/AST/Log compression engine
│   ├── workflows_engine_tool.py # Tinyflows trigger-driven multi-step automation graph
│   ├── multichannel_hub_tool.py # 17-channel dispatcher (Telegram/Discord/Slack/WhatsApp/Gmail)
│   ├── obsidian_knowledge_graph_tool.py # Graphify AST & Obsidian Vault / Canvas generator
│   ├── mempalace_tool.py     # MemPalace verbatim long-term memory & wake-up context
│   ├── img2obj_component_3d_tool.py # Procedural 3D .OBJ/Three.js electronic part builder
│   ├── circuit_templates_tool.py # Parametric circuit generator
│   ├── autorouter_tool.py    # 2-layer grid autorouter & DFM checker
│   ├── manufacturing_tool.py # Turnkey Gerbers, NC drill, CPL, and BOM exporter
│   ├── kicad_editor.py       # S-expression schematic & PCB direct AST editor
│   ├── kicad_tool.py         # KiCad S-expression parser & power tree generator
│   ├── system_control_tool.py# Desktop system control (greeting, app launcher, screenshot, notes)
│   ├── composio_apps_tool.py # Active Discord, Gmail, Calendar, Notion, Docs, Sheets tools
│   ├── thermal_tool.py       # IPC-2221 trace width & regulator thermal solver
│   ├── signal_integrity_tool.py # I2C/UART/CAN signal integrity calculator
│   ├── supply_chain_tool.py  # Component lifecycle & stock risk tracker
│   ├── preferred_parts_tool.py # Preferred component library & workflow memory
│   ├── omniparser_tool.py    # OmniParser V2 GUI screen capture parser
│   ├── datasheet_rag_tool.py # PDF document RAG with Nemotron Embed 1B & ChromaDB
│   ├── nvidia_nim_tool.py    # NVIDIA NIM APIs (FLUX.1, Whisper, Magpie, Nemotron OCR)
│   ├── reach_tool.py         # Web search & compliance checker
│   └── doc_exporter_tool.py  # Engineering & document report exporter
└── tests/                    # 100% Passing Unit & Integration Test Suites
```

---

## ⚡ Quick Start & Running Locally

1. **Activate Python 3.12 Virtual Environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Launch Cyberpunk Web HUD Server**:
   ```powershell
   python web_server.py
   ```
   Open `http://localhost:8000` in your web browser to interact with the WebGL Arc Reactor voice wave visualizer.

3. **Launch Hands-Free Voice Assistant**:
   ```powershell
   python main.py
   ```

4. **Generate & Open the Obsidian Knowledge Graph**:
   ```powershell
   python scratch/run_obsidian_tools.py
   ```
   Open `d:\aaaassistan_pcb\obsidian_vault` in **Obsidian** to view `Architecture_Graph.canvas` and the interactive graph.

5. **Generate 3D Electronic Component Models**:
   ```python
   from tools.img2obj_component_3d_tool import generate_3d_part_from_image_or_spec
   res = generate_3d_part_from_image_or_spec.invoke({"package_or_image": "SOT-223", "output_name": "ams1117_sot223"})
   ```

6. **Run Full Test Suite**:
   ```powershell
   python -m unittest discover tests
   ```

---

## 📜 License & Open-Source Ownership

This project is open-source under the **MIT License**. Created as a personal AI assistant for general work, productivity, automation, and hardware engineering.
