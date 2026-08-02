# 🤖 Jarvis PCB Copilot — AutoPick (Multiverse AI)

A local, voice-activated "Jarvis-style" AI copilot designed for PCB schematic review, electronic component selection, power distribution tree generation, regulatory compliance checks (RoHS/FCC), and servomotor datasheet retrieval for the **AutoPick** robotic arm project at **Multiverse AI**.

![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)
![CUDA 12.1](https://img.shields.io/badge/CUDA-12.1-green.svg)
![PyTorch 2.4.1](https://img.shields.io/badge/PyTorch-2.4.1%2Bcu121-orange.svg)
![LangChain](https://img.shields.io/badge/Orchestration-LangChain-purple.svg)
![Ollama](https://img.shields.io/badge/LLM-Ollama--Llama3-black.svg)
![Kokoro 24kHz](https://img.shields.io/badge/TTS-Kokoro--82M%2024kHz-brightgreen.svg)

---

## ⚡ Hardware Constraints & Resource Distribution

Designed to run smoothly on a Windows laptop with an **Intel Core i5-12450HX CPU**, **24GB RAM**, and an **NVIDIA RTX 3050 Laptop GPU (6GB VRAM)** without VRAM out-of-memory errors:

| Subsystem | Target Processor | Model / Framework | Optimization |
| :--- | :--- | :--- | :--- |
| **Wake Word Engine** | CPU | `openWakeWord` ("hey_jarvis") | ONNX Runtime (CPU) |
| **Speech-to-Text (STT)** | CPU | `Faster-Whisper` (`base.en`) | `INT8` Quantization + Custom Prompt Biasing |
| **Text-to-Speech (TTS)** | CPU | `Kokoro-82M` (24kHz Neural TTS) | ONNX Runtime (`sounddevice` playback) |
| **Orchestration & Memory** | CPU | LangChain + Context Buffer | Async I/O event loop |
| **Core LLM** | GPU (Ollama) | `Llama 3 8B` / `Qwen 2.5 7B` | 4-bit Quantization (~4.5GB VRAM) |
| **Vision & Screen OCR** | GPU / CPU | Microsoft OmniParser V2 + `RapidOCR` | Dynamic ONNX Layout Detection |

---

## 🏗️ Project Architecture & Directory Layout

```
d:/aaaassistan_pcb/
├── config.py                 # System parameters, audio specs, Ollama URL, & STT initial prompt
├── main.py                   # Async main execution loop linking Wake Word -> STT -> LLM -> TTS
├── requirements.txt          # Dependencies with PyTorch CUDA 12.1 index
├── README.md                 # Project documentation
├── voice/
│   ├── __init__.py
│   ├── wakeword.py           # Background openWakeWord listener (CPU ONNX)
│   ├── stt.py                # Faster-Whisper transcriber (CPU INT8) with domain prompt
│   └── tts.py                # Kokoro-82M 24kHz human-like voice synthesis engine
├── agent/
│   ├── __init__.py
│   ├── copilot.py            # LangChain agent with conversation history memory & tool routing
│   └── prompts.py            # System prompts configured for AutoPick / Multiverse AI
├── tools/
│   ├── __init__.py
│   ├── kicad_tool.py         # KiCad schematic/PCB parser, power tree generator, & ERC checks
│   ├── reach_tool.py         # Web search & servomotor datasheet/RoHS compliance checker
│   └── omniparser_tool.py    # OmniParser V2 screen capture & RapidOCR layout parser
├── models/                   # Downloaded ONNX model weights (Kokoro-82M 24kHz voice pack)
└── tests/                    # Unit and integration test suite
    ├── test_kicad_tool.py
    ├── test_reach_tool.py
    ├── test_omniparser_tool.py
    ├── test_agent_copilot.py
    ├── test_agent_memory.py
    └── test_end_to_end.py
```

---

## 🛠️ Key Features & Tools

### 1. KiCad Schematic & PCB Review (`tools/kicad_tool.py`)
- **Direct S-Expression Parsing**: Parses `.kicad_sch` and `.kicad_pcb` files directly without needing KiCad GUI dependencies.
- **Power Distribution Tree**: Generates hierarchical power maps (`12V Motor Rail` -> `5V LDO` -> `3.3V MCU`).
- **Automated ERC Check**: Detects missing ground planes (`GND`), insufficient decoupling capacitors near ICs, and voltage rail isolation risks.
- **Workspace Auto-Discovery**: Automatically locates the active `.kicad_sch` project file in the workspace.

### 2. Web Search & Regulatory Compliance (`tools/reach_tool.py`)
- **Servomotor Datasheet Database**: Embedded technical specifications for **Feetech STS Series** (STS3215, STS3032), **MG996R**, **SG90**, and **ROBOTIS Dynamixel** motors used in the Sim2Real pipeline.
- **Query Cleaning**: Strips conversational filler phrases (*"could you get the datasheet of..."*) to extract clean part queries.
- **Compliance Verification**: Checks **RoHS 3 (2015/863/EU)** lead-free standards and **FCC Part 15** certification status.

### 3. Screen Vision & OCR Parsing (`tools/omniparser_tool.py`)
- **Live GUI Screen Capture**: Captures the primary display monitor (`scratch/screen_capture.png`).
- **RapidOCR ONNX Layout Engine**: Extracts visual schematic section headers (`POWER`, `ENCODERS`, `I2C MUX`), ICs (`TCA9548A`, `LM2596`, `Q1`), and power nets (`12V_PROT`, `+5V`, `+3.3V`, `GND`).

### 4. Context Consciousness & Conversation Memory (`agent/copilot.py`)
- **Multi-Turn Context Memory**: Retains history across conversation turns and caches the last tool execution output.
- **Follow-Up Query Handling**: Understands queries like *"Is the power section in the captured image good?"* or *"What was the last component?"* based on accumulated context.

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

### 4. Start Local Ollama Model
```powershell
# Run Ollama local LLM server
ollama run llama3:8b
```

---

## 🚀 Running Jarvis PCB Copilot

Start the async execution loop:
```powershell
python main.py
```

### 🗣️ Sample Voice Commands

| Category | Voice Command Example | System Action |
| :--- | :--- | :--- |
| **GUI Visual Inspection** | *"Hey Jarvis, capture my screen and describe the circuit."* | Captures screen, runs RapidOCR layout detection, and speaks detected ICs & sections out loud at 24kHz. |
| **Follow-Up Analysis** | *"Hey Jarvis, is the power section in the captured image good?"* | Uses conversation memory to evaluate the `LM2596` buck converter and `Q1` MOSFET in the active schematic. |
| **Power Distribution** | *"Hey Jarvis, generate the power tree for the AutoPick PCB."* | Parses schematic power nets and speaks the 12V -> 5V -> 3.3V rail distribution. |
| **Electrical Rules Check** | *"Hey Jarvis, run an ERC check on my schematic."* | Checks for floating nets, missing ground planes, and decoupling capacitor counts. |
| **Datasheet Search** | *"Hey Jarvis, get the datasheet of servomotor STS."* | Returns torque (19.5 kg-cm @ 7.4V), 12-bit magnetic encoder feedback, and TTL serial bus specs. |
| **Compliance Check** | *"Hey Jarvis, check RoHS and FCC compliance for servomotors."* | Verifies RoHS 3 (2015/863) lead-free certification and FCC status. |

---

## 🧪 Running Automated Unit & Integration Tests

Run the complete test suite:
```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
```

Individual component tests:
```powershell
.venv\Scripts\python.exe -m unittest tests/test_kicad_tool.py
.venv\Scripts\python.exe -m unittest tests/test_reach_tool.py
.venv\Scripts\python.exe -m unittest tests/test_omniparser_tool.py
.venv\Scripts\python.exe -m unittest tests/test_agent_copilot.py
.venv\Scripts\python.exe -m unittest tests/test_agent_memory.py
.venv\Scripts\python.exe -m unittest tests/test_end_to_end.py
```

---

## 📄 License & Credits
Developed for **AutoPick** at **Multiverse AI**. Powered by LangChain, Ollama, openWakeWord, Faster-Whisper, Kokoro-82M, Microsoft OmniParser V2, and KiCad S-Expression tools.
