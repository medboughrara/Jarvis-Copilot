"""
On-Demand Lazy Service Lifecycle Manager for Jarvis Copilot.
Ensures zero-bloat, smooth local execution on consumer laptops (e.g. RTX 3050 GPU, 24GB RAM):
- Heavy AI models (Faster-Whisper, Kokoro ONNX, RapidOCR, ChromaDB Vector Embeddings, Headless Browsers)
  are ONLY loaded into RAM/VRAM on-demand when explicitly requested by a tool.
- Automatically monitors idle time and reclaims memory/VRAM if a service remains unused for >5 minutes.
"""

import os
import time
import gc
import threading
from typing import Dict, Any, Optional, Callable
import config

logger = config.get_logger(__name__)

class ManagedService:
    def __init__(self, name: str, factory: Callable[[], Any], description: str = ""):
        self.name = name
        self.factory = factory
        self.description = description
        self.instance: Optional[Any] = None
        self.last_used: float = 0.0
        self.load_count: int = 0
        self.is_loaded: bool = False

    def acquire(self) -> Any:
        self.last_used = time.time()
        if not self.is_loaded or self.instance is None:
            logger.info(f"[Service Lifecycle] [LOADING] Starting on-demand service: '{self.name}' ({self.description})...")
            start_t = time.time()
            try:
                self.instance = self.factory()
                self.is_loaded = True
                self.load_count += 1
                logger.info(f"[Service Lifecycle] [LOADED] '{self.name}' ready in {(time.time() - start_t)*1000:.1f}ms.")
            except Exception as e:
                logger.error(f"[Service Lifecycle Error in '{self.name}']: {e}")
                self.instance = None
                self.is_loaded = False
                raise e
        return self.instance

    def release(self):
        if self.is_loaded:
            logger.info(f"[Service Lifecycle] [RELEASE] Unloading idle service: '{self.name}' to free memory...")
            self.instance = None
            self.is_loaded = False


class ServiceLifecycleManager:
    def __init__(self):
        self.services: Dict[str, ManagedService] = {}
        self.lock = threading.Lock()
        self._register_factories()

    def _register_factories(self):
        # 1. Kokoro-82M Local Neural TTS ONNX Engine
        self.register_service(
            name="tts_kokoro",
            factory=self._factory_kokoro_tts,
            description="Kokoro-82M ONNX Neural Voice Engine"
        )

        # 2. RapidOCR ONNX Vision Engine
        self.register_service(
            name="ocr_rapid",
            factory=self._factory_rapid_ocr,
            description="RapidOCR ONNX Optical Character Recognition"
        )

        # 3. SentenceTransformers Embeddings Engine
        self.register_service(
            name="embeddings_rag",
            factory=self._factory_embeddings,
            description="SentenceTransformer all-MiniLM-L6-v2 Embeddings"
        )

    def register_service(self, name: str, factory: Callable[[], Any], description: str = ""):
        with self.lock:
            self.services[name] = ManagedService(name, factory, description)

    def get(self, name: str) -> Any:
        with self.lock:
            if name not in self.services:
                raise KeyError(f"Service '{name}' is not registered in ServiceLifecycleManager.")
            service = self.services[name]
        return service.acquire()

    def is_loaded(self, name: str) -> bool:
        with self.lock:
            return self.services.get(name, False) and self.services[name].is_loaded

    def release_idle_services(self, max_idle_seconds: int = 300) -> int:
        """
        Reclaims RAM/VRAM by releasing services that have been idle for longer than max_idle_seconds.
        """
        now = time.time()
        released_count = 0
        with self.lock:
            for s in self.services.values():
                if s.is_loaded and (now - s.last_used) >= max_idle_seconds:
                    s.release()
                    released_count += 1

        if released_count > 0:
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            logger.info(f"[Service Lifecycle] [CLEANUP] Reclaimed {released_count} idle services. Memory freed.")
        return released_count

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            return {
                name: {
                    "is_loaded": s.is_loaded,
                    "load_count": s.load_count,
                    "last_used_ago_sec": round(time.time() - s.last_used, 1) if s.last_used else None,
                    "description": s.description
                }
                for name, s in self.services.items()
            }

    # Factories
    def _factory_kokoro_tts(self):
        from kokoro_onnx import Kokoro
        model_path = "models/kokoro-v1.0.onnx"
        voices_path = "models/voices-v1.0.bin"
        if os.path.exists(model_path) and os.path.exists(voices_path):
            return Kokoro(model_path, voices_path)
        raise FileNotFoundError("Kokoro ONNX model files not found in models/ directory.")

    def _factory_rapid_ocr(self):
        from rapidocr_onnxruntime import RapidOCR
        return RapidOCR()

    def _factory_embeddings(self):
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")


# Global Singleton Lifecycle Instance
service_lifecycle = ServiceLifecycleManager()
