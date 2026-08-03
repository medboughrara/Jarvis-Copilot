"""
Configuration file for Jarvis PCB Copilot (AutoPick / Multiverse AI).
Contains audio specifications, model configurations, and system prompts.
"""

import os
import logging
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure standard structured logging
os.makedirs("scratch", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("scratch/jarvis_session.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def get_logger(name: str):
    return logging.getLogger(name)

# Project Metadata
PROJECT_NAME = "AutoPick"
COMPANY_NAME = "Multiverse AI"
DOMAIN_CONTEXT = "Sim2Real, servomotors, PCB schematics, component compliance"

# Audio Recording Settings
SAMPLE_RATE = 16000  # Required by openWakeWord & Faster-Whisper
CHANNELS = 1         # Mono audio
CHUNK_SIZE = 1280    # openWakeWord expects 80ms chunks (1280 samples at 16kHz)

# Wake Word Configuration
WAKEWORD_MODEL_NAME = "hey_jarvis"  # openWakeWord built-in or custom model
WAKEWORD_THRESHOLD = 0.5            # Sensitivity threshold (0.0 to 1.0)

# Speech-to-Text (Faster-Whisper on CPU)
STT_MODEL_SIZE = "base.en"
STT_DEVICE = "cpu"
STT_COMPUTE_TYPE = "int8"
# Custom initial prompt to bias Whisper for accurate domain transcription
STT_INITIAL_PROMPT = f"{PROJECT_NAME}, {COMPANY_NAME}, Sim2Real, servomotors, PCB, schematic,KiCad, RoHS, FCC"

# Text-to-Speech (Kokoro TTS on CPU)
TTS_MODEL_NAME = "kokoro-v1.0.onnx"
TTS_VOICE = "af_bella"  # Default clean voice
TTS_SPEED = 1.0

# Core LLM Options (Ollama local / Gemini Cloud)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
GEMINI_API_KEYS = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()]
if not GEMINI_API_KEYS and GEMINI_API_KEY:
    GEMINI_API_KEYS = [GEMINI_API_KEY]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
USE_GEMINI = os.getenv("USE_GEMINI", "true").lower() in ("true", "1", "yes")

