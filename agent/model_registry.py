"""
Central Model Registry & Architecture Metadata for Jarvis AI / Jarvis-Copilot.
Classifies foundation models by architectural strengths, parameter scale, context window, and modality:
1. ornith-1.5:9b       -> Local Fast Intent Orchestrator & Reflex Triage (6.6GB, 256K Context)
2. glm-5.3:cloud       -> Flagship Long-Horizon Agentic Coding & Architecture (753B, 1M Context)
3. kimi-k2.7-code:cloud-> Real-World Complex Code Generation & Debugging (1.04T, 256K Context, Vision+Code)
4. glm-5.3-flash:cloud -> Real-Time Multimodal Execution & Fast Tool Calling (321B/18B active, 1M Context)
5. qwen3.8            -> Deep Research, Professional Work & Mathematical Reasoning (27B/8B, 128K Context)
6. gemini-2.5-flash    -> High-Throughput Cloud Multi-Key Pool (1M Context)
7. llama3:8b          -> Local GPU/CPU Zero-Downtime Offline Fallback (8B, 8K Context)

Includes singleton client factory caching (resolving Finding 3.7 - re-instantiation of heavy clients).
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import config

logger = config.get_logger(__name__)


@dataclass
class ModelSpec:
    model_id: str
    name: str
    provider: str  # "ollama_cloud", "ollama_local", "gemini", "nvidia"
    parameters: str
    context_window: int
    modalities: List[str]  # ["text", "vision", "tools", "thinking"]
    specialization_domain: str  # "local_orchestration", "coding_flagship", "coding_implementation", "multimodal_flash", "research_reasoning", "general_cloud", "local_offline"
    description: str
    recommended_temperature: float = 0.3
    active_in_pool: bool = True


class ModelRegistry:
    """Central registry and client factory for multi-model agentic environments."""

    def __init__(self):
        self.models: Dict[str, ModelSpec] = {}
        self._client_cache: Dict[str, Any] = {}
        self._register_default_models()

    def _register_default_models(self):
        # 1. Local Fast Orchestrator: Ornith-1.5 (9B)
        self.register(ModelSpec(
            model_id="ornith-1.5:9b",
            name="Ornith 1.5 (9B Local Foundation)",
            provider="ollama_local",
            parameters="9B (6.6 GB)",
            context_window=262144,  # 256K
            modalities=["text", "vision", "tools"],
            specialization_domain="local_orchestration",
            description="Lightweight local foundation model for <100ms intent classification, triage, and fast reflex response."
        ))

        # 2. Flagship Agentic Coding: GLM-5.3 (753B)
        self.register(ModelSpec(
            model_id="glm-5.3:cloud",
            name="GLM 5.3 (Flagship 753B)",
            provider="ollama_cloud",
            parameters="753B",
            context_window=1048576,  # 1M
            modalities=["text", "tools", "thinking"],
            specialization_domain="coding_flagship",
            description="Z.ai flagship model and most capable open-weights model for long-horizon agentic coding and deep system architecture."
        ))

        # 3. Complex Code Generation & Debugging: Kimi K2.7 Code (1.04T)
        self.register(ModelSpec(
            model_id="kimi-k2.7-code:cloud",
            name="Kimi K2.7 Code (1.04T Multimodal Code)",
            provider="ollama_cloud",
            parameters="1.04T",
            context_window=262144,  # 256K
            modalities=["text", "vision", "tools", "thinking"],
            specialization_domain="coding_implementation",
            description="Moonshot AI coding-focused agentic model with substantial gains on real-world long-horizon coding tasks and 30% lower thinking-token usage."
        ))

        # 4. Fast Multimodal & Real-Time Tool Calling: GLM-5.3 Flash (321B / 18B active)
        self.register(ModelSpec(
            model_id="glm-5.3-flash:cloud",
            name="GLM 5.3 Flash (321B Multimodal MoE)",
            provider="ollama_cloud",
            parameters="321B (18B active MoE)",
            context_window=1048576,  # 1M
            modalities=["text", "vision", "tools", "thinking"],
            specialization_domain="multimodal_flash",
            description="Natively multimodal high-speed agentic model for instant tool executions, visual PCB inspection, and quality gate verification."
        ))

        # 5. Deep Research & Professional Reasoning: Qwen 3.8 (27B)
        self.register(ModelSpec(
            model_id="qwen3.8",
            name="Qwen 3.8 (27B Dense Reasoning)",
            provider="ollama_cloud",
            parameters="27B",
            context_window=131072,  # 128K
            modalities=["text", "vision", "tools", "thinking"],
            specialization_domain="research_reasoning",
            description="Alibaba Qwen model delivering substantial gains across coding, professional work, research, and mathematical reasoning."
        ))

        # 6. General High-Throughput Cloud Pool: Gemini 2.5 Flash
        self.register(ModelSpec(
            model_id="gemini-2.5-flash",
            name="Google Gemini 2.5 Flash",
            provider="gemini",
            parameters="Proprietary Multimodal",
            context_window=1048576,  # 1M
            modalities=["text", "vision", "tools"],
            specialization_domain="general_cloud",
            description="Google foundation multimodal model backed by automated multi-key round-robin rotation and 429 rate limit cooling."
        ))

        # 7. Local Offline Fallback: Llama 3 8B
        self.register(ModelSpec(
            model_id="llama3:8b",
            name="Llama 3 (8B Local Offline)",
            provider="ollama_local",
            parameters="8B",
            context_window=8192,
            modalities=["text", "tools"],
            specialization_domain="local_offline",
            description="Zero-downtime offline fallback model running on local GPU (RTX 3050) / CPU."
        ))

    def register(self, spec: ModelSpec):
        self.models[spec.model_id] = spec

    def get_model_spec(self, model_id: str) -> Optional[ModelSpec]:
        return self.models.get(model_id)

    def get_models_by_domain(self, domain: str) -> List[ModelSpec]:
        return [m for m in self.models.values() if m.specialization_domain == domain and m.active_in_pool]

    def list_all_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "model_id": m.model_id,
                "name": m.name,
                "provider": m.provider,
                "parameters": m.parameters,
                "context_window": m.context_window,
                "modalities": m.modalities,
                "domain": m.specialization_domain,
                "description": m.description,
                "active": m.active_in_pool
            }
            for m in self.models.values()
        ]

    # --- Singleton Client Factory (Resolving Finding 3.7) ---

    def get_client(self, model_id: str, temperature: float = None, scoped_tools: list = None) -> Any:
        """
        Returns a cached, reusable LLM client instance for the requested model_id.
        Avoids expensive per-call re-instantiation.
        """
        spec = self.get_model_spec(model_id)
        if not spec:
            raise ValueError(f"Unknown model_id '{model_id}' in ModelRegistry.")

        temp = temperature if temperature is not None else spec.recommended_temperature

        # Create or fetch client
        if spec.provider in ["ollama_local", "ollama_cloud"]:
            from langchain_ollama import ChatOllama
            cache_key = f"{model_id}:{temp}"
            if cache_key not in self._client_cache:
                base_url = config.OLLAMA_BASE_URL
                self._client_cache[cache_key] = ChatOllama(
                    model=model_id,
                    base_url=base_url,
                    temperature=temp
                )
            client = self._client_cache[cache_key]
            if scoped_tools and hasattr(client, "bind_tools"):
                return client.bind_tools(scoped_tools)
            return client

        elif spec.provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            api_key = config.settings.GEMINI_API_KEYS[0] if config.settings.GEMINI_API_KEYS else None
            cache_key = f"{model_id}:{temp}:{api_key[:8] if api_key else 'none'}"
            if cache_key not in self._client_cache:
                self._client_cache[cache_key] = ChatGoogleGenerativeAI(
                    model=model_id,
                    api_key=api_key,
                    temperature=temp,
                    timeout=25,
                    max_retries=1
                )
            client = self._client_cache[cache_key]
            if scoped_tools and hasattr(client, "bind_tools"):
                return client.bind_tools(scoped_tools)
            return client

        raise ValueError(f"Unsupported provider '{spec.provider}' for model '{model_id}'.")


# Global Singleton Model Registry
model_registry = ModelRegistry()
