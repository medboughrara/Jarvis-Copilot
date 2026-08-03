# 🤖 Jarvis PCB Copilot — AutoPick (Multiverse AI)

A local, voice-activated "Jarvis-style" AI copilot designed for PCB schematic review, electronic component selection, power distribution tree generation, regulatory compliance checks (RoHS/FCC), IPC-2221 thermal analysis, signal integrity, supply chain EOL tracking, and servomotor datasheet retrieval for the **AutoPick** robotic arm project at **Multiverse AI**.

![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)
![CUDA 12.1](https://img.shields.io/badge/CUDA-12.1-green.svg)
![PyTorch 2.4.1](https://img.shields.io/badge/PyTorch-2.4.1%2Bcu121-orange.svg)
![LangChain](https://img.shields.io/badge/Orchestration-LangChain-purple.svg)
![Gemini 3.6 Flash](https://img.shields.io/badge/LLM-Gemini%203.6%20Flash-blue.svg)
![MCP Server](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol-red.svg)
![Kokoro 24kHz](https://img.shields.io/badge/TTS-Kokoro--82M%2024kHz-brightgreen.svg)

---

> [!WARNING]
> **Safety & Scope Disclaimer**: Jarvis PCB Copilot is an assistive AI engineering copilot designed for rapid schematic context retrieval, IPC-2221 trace calculation, and preliminary ERC checking. It is **NOT** a substitute for human peer review by a licensed electrical engineer or KiCad's built-in, certified DRC/ERC layout engines. Always manually verify motor supply rail trace widths, high-current isolation gaps, and polarity prior to PCB manufacturing.

---

## ⚡ Hardware Constraints & Resource Distribution

Designed to run smoothly on a Windows laptop with an **Intel Core i5-12450HX CPU**, **24GB RAM**, and an **NVIDIA RTX 3050 Laptop GPU (6GB VRAM)** without VRAM out-of-memory errors:

| Subsystem | Target Processor | Model / Framework | Optimization |
| :--- | :--- | :--- | :--- |
| **Wake Word Engine** | CPU | `openWakeWord` ("hey_jarvis") | ONNX Runtime (CPU) |
| **Speech-to-Text (STT)** | CPU | `Faster-Whisper` (`base.en`) | `INT8` Quantization + Custom Prompt Biasing |
| **Text-to-Speech (TTS)** | CPU | `Kokoro-82M` (24kHz Neural TTS) | ONNX Runtime (`sounddevice` non-blocking audio) |
| **Orchestration & Memory** | CPU | LangChain + Context Buffer | Async I/O event loop |
| **LLM Tier 1 (Cloud)** | Cloud Pool | `Google Gemini 3.6 Flash` (5 API Keys) | Round-Robin Rotation + 429 Rate Limit Cooling |
| **LLM Tier 2 (Cloud)** | Cloud Pool | `Ollama Cloud` (`glm-5.2:cloud`, `kimi-k3:cloud`) | Secondary Cloud Fallback |
| **LLM Tier 3 (Local)** | GPU RTX 3050 | `Llama 3 8B` (`ChatOllama`) | Zero-Downtime Offline Fallback |
| **Vision & Screen OCR** | GPU / CPU | Microsoft OmniParser V2 + `RapidOCR` | Dynamic ONNX Layout Detection |
| **Protocol Integration** | CPU / Stdio | `FastMCP` Stdio MCP Server | Native IDE Integration (Antigravity/Cursor/Claude) |

---

## 🏗️ Project Architecture & Directory Layout

```
d:/aaaassistan_pcb/
├── config.py                 # System parameters, audio specs, multi-key config, & Ollama URL
├── main.py                   # Async main execution loop linking Wake Word -> STT -> LLM -> TTS
├── mcp_server.py             # Stdio Model Context Protocol (MCP) server for external IDEs
├── requirements.txt          # Dependencies with PyTorch CUDA 12.1 index & MCP packages
├── README.md                 # Project documentation
├── voice/
│   ├── __init__.py
│   ├── wakeword.py           # Background openWakeWord listener (CPU ONNX)
│   ├── stt.py                # Faster-Whisper transcriber (CPU INT8) with domain prompt
│   └── tts.py                # Kokoro-82M 24kHz non-blocking voice synthesis engine
├── agent/
│   ├── __init__.py
│   ├── copilot.py            # LangChain agent with conversation history & 3-tier LLM fallback
│   ├── key_manager.py        # Multi-key Gemini rotation manager & real-time metrics tracking
│   ├── skill_loader.py       # Standardized AAS SKILL.md playbook loader
│   ├── workflows.py          # Multi-stage autonomous audit workflows & report generator
│   └── prompts.py            # System prompts configured for AutoPick / Multiverse AI
├── skills/                   # AAS-style SKILL.md hardware engineering playbooks
│   ├── pcb-thermal-analysis/SKILL.md
│   ├── emc-emi-hardening/SKILL.md
│   └── sim2real-motor-calibration/SKILL.md
├── tools/
│   ├── __init__.py
│   ├── kicad_tool.py         # KiCad schematic parser, BOM generation, power tree, & ERC checks
│   ├── reach_tool.py         # Web search & servomotor datasheet/RoHS compliance checker
│   ├── thermal_tool.py       # IPC-2221 trace width, copper power loss, & regulator thermal calculation
│   ├── signal_integrity_tool.py # I2C pull-up bounds, UART damping, & CAN bus termination
│   ├── supply_chain_tool.py  # Component lifecycle (Active/NRND/EOL) & distributor stock risk
│   ├── omniparser_tool.py    # OmniParser V2 screen capture & RapidOCR layout parser
│   └── datasheet_rag_tool.py # Local PDF RAG with sentence-transformers and ChromaDB
├── models/                   # Downloaded ONNX model weights (Kokoro-82M 24kHz voice pack)
├── datasheets/               # Directory for local PDF datasheets queried via RAG
├── scratch/                  # Directory for audit reports, CSVs, screen captures, and key stats
├── Dockerfile                # Container configuration with system audio dependencies
├── CONTRIBUTING.md           # Developer guidelines
├── LICENSE                   # MIT License
└── tests/                    # Unit and integration test suite (26 test modules)
```

---

## 🛠️ Key Features & Tools

### 1. Multi-Key Gemini API Key Rotation & Tracking (`agent/key_manager.py`)
- **Round-Robin Key Balancing**: Automatically cycles requests across 5 registered Gemini API keys.
- **429 Rate Limit Cooldown**: Automatically detects rate limits (`429 Resource Exhausted`), puts the affected key into a temporary 60-second cooldown, and seamlessly rotates to the next available key without interrupting the user.
- **Usage Metrics Tracking**: Tracks request counts, error counts, last used timestamps, and outputs ASCII tracking tables.

### 2. Hierarchical 3-Tier LLM Pipeline (`agent/copilot.py`)
- **Tier 1 (Primary)**: Google Gemini 3.6 Flash Multi-Key Cloud Engine.
- **Tier 2 (Secondary Cloud)**: Ollama Cloud Models (`glm-5.2:cloud`, `kimi-k3:cloud`).
- **Tier 3 (Local Fallback)**: Local `ChatOllama` (`llama3:8b`) for complete offline operation.

### 3. Native Stdio Model Context Protocol (MCP) Server (`mcp_server.py`)
- **IDE Tool Exporter**: Powered by `FastMCP`, exposing all 11 hardware tools over stdio.
- **Cross-Platform Agent Integration**: Allows Cursor, Antigravity, Claude Code, and VS Code to call Jarvis PCB Copilot tools directly from your editor.

### 4. AAS Core Playbook Engine (`agent/skill_loader.py` & `skills/`)
- **Dynamic Playbooks**: Reads AAS-style `SKILL.md` markdown playbooks with YAML frontmatter.
- **Domain Playbooks**: Includes pre-built playbooks for PCB thermal analysis, EMC/EMI hardening, and Sim2Real motor calibration.

### 5. Specialized Hardware Engineering Tools
- **IPC-2221 Thermal Calculator (`tools/thermal_tool.py`)**: Computes copper trace width requirements ($I = k \cdot \Delta T^{0.44} \cdot A^{0.725}$), $I^2R$ power loss, and SOT-223 regulator junction thermal rise ($T_j = T_a + P_d \cdot R_{\theta JA}$).
- **Signal Integrity Calculator (`tools/signal_integrity_tool.py`)**: Computes I2C pull-up resistor min/max bounds ($R_{min} / R_{max}$), UART damping resistors, and CAN bus split termination.
- **Supply Chain EOL Tracker (`tools/supply_chain_tool.py`)**: Checks component lifecycle status (Active vs NRND vs EOL) and distributor stock availability.

### 6. Autonomous Multi-Phase Audit Workflows (`agent/workflows.py`)
- **6-Stage Hardware Review**: Runs Schematic Parse -> ERC Checks -> Power Tree -> Thermal Analysis -> Signal Integrity -> Supply Chain.
- **Reproducible Artifacts**: Automatically saves audit output to `scratch/pcb_audit_report.json` and `scratch/pcb_audit_report.md`.

---

## 📥 Installation & Setup Guide

### 1. Prerequisites
- **Python 3.12** installed on Windows.
- **NVIDIA GPU Drivers** and **CUDA 12.1** toolkit.
- **Ollama** installed on Windows.

### 2. Create Virtual Environment with `uv`
```powershell
# Navigate to workspace
cd d:\aaaassistan_pcb

# Create Python 3.12 virtual environment
uv venv --python 3.12 --clear .venv

# Activate virtual environment
.venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
# Install project packages
uv pip install --index-strategy unsafe-best-match -r requirements.txt

# Install PyTorch CUDA 12.1 wheels
uv pip install torch==2.4.1+cu121 torchaudio==2.4.1+cu121 torchvision==0.19.1+cu121 --index-url https://download.pytorch.org/whl/cu121
```

### 4. Environment Variables Configuration (`.env`)
Create a `.env` file in the root directory:
```env
GEMINI_API_KEYS=AIzaSyDl...,AQ.Ab8RN...,AQ.Ab8RN...,AQ.Ab8RN...,AQ.Ab8RN...
USE_GEMINI=true
GEMINI_MODEL=gemini-3.6-flash
OLLAMA_CLOUD_MODELS=glm-5.2:cloud,kimi-k3:cloud
OLLAMA_MODEL=llama3:8b
```

---

## 🚀 Running Jarvis PCB Copilot

### Option A: Voice Assistant Mode
```powershell
python main.py
```

### Option B: Native Stdio MCP Server Mode (for Cursor / Antigravity / Claude Code)
```powershell
python mcp_server.py
```

---

## 🗣️ Sample Voice Commands

| Category | Voice Command Example | System Action |
| :--- | :--- | :--- |
| **Autonomous Audit** | *"Hey Jarvis, run a full PCB audit workflow."* | Executes 6-stage hardware review and writes reports to `scratch/pcb_audit_report.md`. |
| **IPC Thermal Loss** | *"Hey Jarvis, calculate thermal power loss for 3 Amps."* | Evaluates IPC-2221 trace width, mOhm resistance, and SOT-223 LDO junction temperature. |
| **Signal Integrity** | *"Hey Jarvis, calculate I2C pullup resistors for 400kHz."* | Computes $R_{min}$ and $R_{max}$ resistor bounds based on bus capacitance. |
| **Supply Chain EOL** | *"Hey Jarvis, check supply chain status for STM32F405."* | Checks lifecycle status (Active), distributor stock, and second-source pinouts. |
| **GUI Visual Inspection** | *"Hey Jarvis, capture my screen and describe the circuit."* | Captures display, runs RapidOCR layout detection, and speaks detected ICs out loud at 24kHz. |
| **Power Distribution** | *"Hey Jarvis, generate the power tree for the AutoPick PCB."* | Parses schematic power nets and speaks the 12V -> 5V -> 3.3V rail distribution. |
| **Electrical Rules Check** | *"Hey Jarvis, run an ERC check on my schematic."* | Checks for floating nets, missing ground planes, and decoupling capacitor counts. |
| **API Key Status** | *"Hey Jarvis, show API key tracking status."* | Outputs ASCII table of all 5 Gemini keys, request counts, error counts, and status. |

---

## 🧪 Running Automated Unit & Integration Tests

Run the complete 26-module test suite:
```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
```

---

## 📄 License & Credits
Developed for **AutoPick** at **Multiverse AI**. Powered by LangChain, Google Gemini, Ollama, FastMCP, openWakeWord, Faster-Whisper, Kokoro-82M, Microsoft OmniParser V2, and KiCad S-Expression tools.
