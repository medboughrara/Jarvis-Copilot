"""
Configuration file and validated Pydantic Settings schema for Jarvis PCB Copilot.
"""

import os
import sys
import logging
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

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


class JarvisConfig(BaseSettings):
    """Pydantic Settings Schema for Jarvis PCB Copilot with fail-fast startup validation."""

    # Project Metadata
    PROJECT_NAME: str = "Jarvis AI Assistant"
    COMPANY_NAME: str = "Personal Open Source"
    DOMAIN_CONTEXT: str = "PCB schematics, component compliance, signal integrity, thermal analysis"

    # Audio Recording Settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1280

    # Wake Word Configuration
    WAKEWORD_MODEL_NAME: str = "jarvis"
    WAKEWORD_THRESHOLD: float = 0.5

    # Speech-to-Text
    STT_MODEL_SIZE: str = "base.en"
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"
    STT_INITIAL_PROMPT: str = "Jarvis, check my calendar, draft an email, review my code, summarize this document, analyze my schematic, search the web."

    # Text-to-Speech
    TTS_MODEL_NAME: str = "kokoro-v1.0.onnx"
    TTS_VOICE: str = "af_bella"
    TTS_SPEED: float = 1.0

    # Multi-Model Specialized Agentic Suite (Ollama & Cloud)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llama3:8b")
    OLLAMA_SLM_MODEL: str = Field(default="llama3.2:1b")
    USE_STAGE1_LOCAL_SLM: bool = Field(default=True)
    OLLAMA_LOCAL_ORCHESTRATOR_MODEL: str = Field(default="ornith-1.5:9b")
    OLLAMA_FLAGSHIP_CODING_MODEL: str = Field(default="glm-5.3:cloud")
    OLLAMA_CODE_AGENT_MODEL: str = Field(default="kimi-k2.7-code:cloud")
    OLLAMA_MULTIMODAL_FLASH_MODEL: str = Field(default="glm-5.3-flash:cloud")
    OLLAMA_RESEARCH_MODEL: str = Field(default="qwen3.8")
    OLLAMA_CLOUD_MODELS_RAW: str = Field(
        default="glm-5.3:cloud,kimi-k2.7-code:cloud,glm-5.3-flash:cloud,qwen3.8,ornith-1.5:9b",
        validation_alias="OLLAMA_CLOUD_MODELS"
    )
    
    GEMINI_API_KEYS_RAW: str = Field(default="", validation_alias="GEMINI_API_KEYS")
    GEMINI_API_KEY_RAW: str = Field(default="", validation_alias="GEMINI_API_KEY")
    GOOGLE_API_KEY_RAW: str = Field(default="", validation_alias="GOOGLE_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_MODEL")
    USE_GEMINI: bool = Field(default=True)

    # NVIDIA NIM Cloud Foundation Models
    NVIDIA_API_KEY: str = Field(default="", validation_alias="NVIDIA_API_KEY")
    NVIDIA_KIMI_KEY: str = Field(default="", validation_alias="NVIDIA_KIMI_KEY")
    NVIDIA_NEMOTRON_KEY: str = Field(default="", validation_alias="NVIDIA_NEMOTRON_KEY")
    NVIDIA_NEMOTRON_OCR_KEY: str = Field(default="", validation_alias="NVIDIA_NEMOTRON_OCR_KEY")
    NVIDIA_NEMOTRON_EMBED_KEY: str = Field(default="", validation_alias="NVIDIA_NEMOTRON_EMBED_KEY")

    NVIDIA_FLUX_URL: str = Field(default="https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell")
    NVIDIA_WHISPER_URL: str = Field(default="https://ai.api.nvidia.com/v1/audio/openai/whisper-large-v3")
    NVIDIA_MAGPIE_URL: str = Field(default="https://ai.api.nvidia.com/v1/audio/nvidia/magpie-tts-multilingual")
    NVIDIA_INTEGRATE_CHAT_URL: str = Field(default="https://integrate.api.nvidia.com/v1/chat/completions")
    NVIDIA_NEMOTRON_OCR_URL: str = Field(default="https://ai.api.nvidia.com/v1/vlm/nvidia/nemotron-ocr-v2")
    NVIDIA_EMBED_URL: str = Field(default="https://integrate.api.nvidia.com/v1/embeddings")

    USE_NVIDIA_STT: bool = Field(default=False)
    USE_NVIDIA_TTS: bool = Field(default=False)

    # Baidu Unlimited-OCR Model Config
    UNLIMITED_OCR_MODEL: str = Field(default="baidu/Unlimited-OCR")
    USE_UNLIMITED_OCR: bool = Field(default=True)

    # Composio MCP Integration
    COMPOSIO_API_KEY: str = Field(default="", validation_alias="COMPOSIO_API_KEY")
    COMPOSIO_MCP_URL: str = Field(default="https://connect.composio.dev/mcp")

    # Autonomous TaskRunner & Parallel Execution
    SEARCH_ONLY_ON_EXPLICIT_REQUEST: bool = Field(default=True)
    MAX_PARALLEL_TASKS: int = Field(default=4)
    MAX_PARALLEL_CLOUD_CALLS: int = Field(default=5)
    MAX_PARALLEL_LOCAL_GPU_CALLS: int = Field(default=1)  # Strict serialization for 6GB RTX 3050 VRAM
    CODE_SANDBOX_TIMEOUT_SECONDS: int = Field(default=15)
    CODE_SANDBOX_MAX_MEMORY_MB: int = Field(default=256)
    CODE_PIPELINE_MAX_RETRIES: int = Field(default=2)
    TASK_RUNNER_DB_PATH: str = Field(default="data/task_runner.db")
    AUDIT_LOG_DB_PATH: str = Field(default="data/audit_log.db")
    TRUSTED_ORIGINS_RAW: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000",
        validation_alias="TRUSTED_ORIGINS"
    )

    # Desktop Pet & Screen Copilot Settings
    PET_ENABLED: bool = Field(default=True)
    PET_HOTKEY: str = Field(default="ctrl+space")
    PET_IDLE_TIMEOUT_SECONDS: int = Field(default=120)
    PET_LOCAL_VISION_ONLY: bool = Field(default=True)
    PET_TRUSTED_ORIGINS_RAW: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000",
        validation_alias="PET_TRUSTED_ORIGINS"
    )

    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def GEMINI_API_KEYS(self) -> List[str]:
        keys = [k.strip() for k in self.GEMINI_API_KEYS_RAW.split(",") if k.strip()]
        if not keys:
            single = self.GEMINI_API_KEY_RAW.strip() or self.GOOGLE_API_KEY_RAW.strip()
            if single:
                keys = [single]
        return keys

    @property
    def OLLAMA_CLOUD_MODELS(self) -> List[str]:
        return [m.strip() for m in self.OLLAMA_CLOUD_MODELS_RAW.split(",") if m.strip()]

    @property
    def TRUSTED_ORIGINS(self) -> List[str]:
        return [o.strip() for o in self.TRUSTED_ORIGINS_RAW.split(",") if o.strip()]

    @property
    def PET_TRUSTED_ORIGINS(self) -> List[str]:
        raw = self.PET_TRUSTED_ORIGINS_RAW.strip()
        if not raw:
            return self.TRUSTED_ORIGINS
        return [o.strip() for o in raw.split(",") if o.strip()]

    def validate_configuration(self):
        """Ensures at least 1 LLM tier is properly configured."""
        has_gemini = bool(self.USE_GEMINI and self.GEMINI_API_KEYS)
        has_nvidia = bool(self.NVIDIA_API_KEY or self.NVIDIA_KIMI_KEY or self.NVIDIA_NEMOTRON_KEY)
        has_ollama_cloud = bool(self.OLLAMA_CLOUD_MODELS)
        has_ollama_local = bool(self.OLLAMA_BASE_URL and self.OLLAMA_MODEL)

        if not (has_gemini or has_nvidia or has_ollama_cloud or has_ollama_local):
            raise ValueError(
                "Invalid Configuration: No active LLM tier configured. "
                "Please configure GEMINI_API_KEYS, NVIDIA_API_KEY, OLLAMA_CLOUD_MODELS, or local OLLAMA_BASE_URL in your .env file."
            )


# Initialize and validate singleton config instance at startup
_config_instance = JarvisConfig()
_config_instance.validate_configuration()

# Primary typed access point
settings = _config_instance

# Export backward-compatible module-level globals
PROJECT_NAME = _config_instance.PROJECT_NAME
COMPANY_NAME = _config_instance.COMPANY_NAME
DOMAIN_CONTEXT = _config_instance.DOMAIN_CONTEXT
SAMPLE_RATE = _config_instance.SAMPLE_RATE
CHANNELS = _config_instance.CHANNELS
CHUNK_SIZE = _config_instance.CHUNK_SIZE
WAKEWORD_MODEL_NAME = _config_instance.WAKEWORD_MODEL_NAME
WAKEWORD_THRESHOLD = _config_instance.WAKEWORD_THRESHOLD
STT_MODEL_SIZE = _config_instance.STT_MODEL_SIZE
STT_DEVICE = _config_instance.STT_DEVICE
STT_COMPUTE_TYPE = _config_instance.STT_COMPUTE_TYPE
STT_INITIAL_PROMPT = _config_instance.STT_INITIAL_PROMPT
TTS_MODEL_NAME = _config_instance.TTS_MODEL_NAME
TTS_VOICE = _config_instance.TTS_VOICE
TTS_SPEED = _config_instance.TTS_SPEED
OLLAMA_BASE_URL = _config_instance.OLLAMA_BASE_URL
OLLAMA_MODEL = _config_instance.OLLAMA_MODEL
OLLAMA_CLOUD_MODELS = _config_instance.OLLAMA_CLOUD_MODELS
GEMINI_API_KEY = _config_instance.GEMINI_API_KEY_RAW or (_config_instance.GEMINI_API_KEYS[0] if _config_instance.GEMINI_API_KEYS else "")
GEMINI_API_KEYS = _config_instance.GEMINI_API_KEYS
GEMINI_MODEL = _config_instance.GEMINI_MODEL
USE_GEMINI = _config_instance.USE_GEMINI
NVIDIA_API_KEY = _config_instance.NVIDIA_API_KEY
NVIDIA_KIMI_KEY = _config_instance.NVIDIA_KIMI_KEY
NVIDIA_NEMOTRON_KEY = _config_instance.NVIDIA_NEMOTRON_KEY
NVIDIA_NEMOTRON_OCR_KEY = _config_instance.NVIDIA_NEMOTRON_OCR_KEY
NVIDIA_NEMOTRON_EMBED_KEY = _config_instance.NVIDIA_NEMOTRON_EMBED_KEY
NVIDIA_FLUX_URL = _config_instance.NVIDIA_FLUX_URL
NVIDIA_WHISPER_URL = _config_instance.NVIDIA_WHISPER_URL
NVIDIA_MAGPIE_URL = _config_instance.NVIDIA_MAGPIE_URL
NVIDIA_INTEGRATE_CHAT_URL = _config_instance.NVIDIA_INTEGRATE_CHAT_URL
NVIDIA_NEMOTRON_OCR_URL = _config_instance.NVIDIA_NEMOTRON_OCR_URL
NVIDIA_EMBED_URL = _config_instance.NVIDIA_EMBED_URL
USE_NVIDIA_STT = _config_instance.USE_NVIDIA_STT
USE_NVIDIA_TTS = _config_instance.USE_NVIDIA_TTS
UNLIMITED_OCR_MODEL = _config_instance.UNLIMITED_OCR_MODEL
USE_UNLIMITED_OCR = _config_instance.USE_UNLIMITED_OCR
COMPOSIO_API_KEY = _config_instance.COMPOSIO_API_KEY
COMPOSIO_MCP_URL = _config_instance.COMPOSIO_MCP_URL
