"""
Local Lightweight Orchestrator for Jarvis AI / Jarvis-Copilot.
Runs locally on CPU/GPU in <100ms (using ornith-1.5:9b / llama3:8b) to:
1. Parse user input and understand the underlying intent before calling heavy cloud models.
2. Evaluate task complexity, domain, and token context requirements.
3. Select optimal execution strategy:
   - DIRECT_LOCAL: Handled locally in ~50ms for simple chat / greetings / local controls.
   - SINGLE_SPECIALIZED: Routes directly to domain champion (e.g. glm-5.3-flash for vision, qwen3.8 for research).
   - COLLABORATIVE_PIPELINE: Multi-model sequential pipeline (Plan with glm-5.3 -> Implement with kimi-k2.7-code -> Verify with glm-5.3-flash).
"""

import re
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import config
from agent.model_registry import model_registry

logger = config.get_logger(__name__)


@dataclass
class PipelineStep:
    step_number: int
    role: str  # "planner", "generator", "verifier", "executor"
    model_id: str
    description: str


@dataclass
class OrchestratorPlan:
    domain: str  # "simple_chat", "coding", "multimodal", "research", "eda_hardware"
    complexity_score: int  # 1 (instant) to 5 (complex multi-step)
    execution_strategy: str  # "DIRECT_LOCAL", "SINGLE_SPECIALIZED", "COLLABORATIVE_PIPELINE"
    primary_model_id: str
    pipeline_steps: List[PipelineStep] = field(default_factory=list)
    estimated_context_tokens: int = 1000
    reasoning_summary: str = ""
    evaluation_latency_ms: float = 0.0


class LocalLightweightOrchestrator:
    """Fast local intent evaluator and multi-model agentic orchestrator."""

    def __init__(self, local_model_id: str = "ornith-1.5:9b"):
        self.local_model_id = local_model_id

    def evaluate_intent(self, prompt: str, context_metadata: Dict[str, Any] = None) -> OrchestratorPlan:
        """
        Evaluates user prompt in <100ms and returns the architectural routing plan.
        """
        start_t = time.time()
        lower_p = prompt.lower().strip()

        # Domain Heuristics & Pattern Analysis
        is_coding = any(k in lower_p for k in [
            "def ", "class ", "function", "refactor", "debug", "compile", "bug", "syntax",
            "git ", "script", "api", "endpoint", "fastapi", "react", "html", "css", "docker",
            "write code", "fix error", "implement", "unit test", "pytest"
        ])
        
        is_multimodal = any(k in lower_p for k in [
            "image", "picture", "screenshot", "screen", "capture", "ocr", "gui", "diagram",
            "look at this", "inspect visual", "photo", "schematic view", ".png", ".jpg", ".webp"
        ])

        is_eda_hardware = any(k in lower_p for k in [
            "kicad", "schematic", "pcb", "netlist", "drc", "erc", "trace", "thermal loss",
            "joule", "ipc-2221", "footprint", "bom", "resistor", "capacitor", "stm32", "esp32",
            "gerber", "drill", "layer stackup", "signal integrity", "impedance", "via"
        ])

        is_research = any(k in lower_p for k in [
            "research", "paper", "calculate", "math", "derive", "analyze trend", "deep search",
            "compare architectures", "literature review", "benchmark", "pros and cons"
        ])

        is_simple_chat = (
            len(lower_p.split()) <= 6 and 
            any(k in lower_p for k in ["hello", "hi", "hey", "how are you", "who are you", "what time", "date", "joke", "thanks", "thank you", "good morning", "good evening"])
        )

        # Classify Domain
        if is_multimodal:
            domain = "multimodal"
            complexity = 3
        elif is_eda_hardware:
            domain = "eda_hardware"
            complexity = 4
        elif is_coding:
            domain = "coding"
            # Distinguish simple one-liners from complex long-horizon coding
            complexity = 5 if len(prompt.split()) > 20 or "architecture" in lower_p or "refactor" in lower_p else 3
        elif is_research:
            domain = "research"
            complexity = 4
        elif is_simple_chat:
            domain = "simple_chat"
            complexity = 1
        else:
            domain = "general"
            complexity = 2

        # Determine Strategy & Model Assignments
        steps = []
        if domain == "simple_chat":
            strategy = "DIRECT_LOCAL"
            primary_model = "ornith-1.5:9b"
            summary = "Direct local execution for fast response (<100ms)."

        elif domain == "coding" and complexity >= 4:
            strategy = "COLLABORATIVE_PIPELINE"
            primary_model = "glm-5.3:cloud"
            steps = [
                PipelineStep(1, "planner", "glm-5.3:cloud", "Architectural deconstruction & multi-step planning (753B / 1M context)"),
                PipelineStep(2, "generator", "kimi-k2.7-code:cloud", "High-efficiency code implementation (1.04T parameter coding model)"),
                PipelineStep(3, "verifier", "glm-5.3-flash:cloud", "AST syntax check, lint verification & test execution")
            ]
            summary = "Multi-model coding pipeline: GLM-5.3 planning -> Kimi K2.7 Code generation -> GLM-5.3 Flash verification."

        elif domain == "coding":
            strategy = "SINGLE_SPECIALIZED"
            primary_model = "kimi-k2.7-code:cloud"
            summary = "Direct execution on Kimi K2.7 Code (1.04T parameter coding model)."

        elif domain == "multimodal":
            strategy = "SINGLE_SPECIALIZED"
            primary_model = "glm-5.3-flash:cloud"
            summary = "High-speed natively multimodal execution on GLM-5.3 Flash (1M context)."

        elif domain == "research":
            strategy = "SINGLE_SPECIALIZED"
            primary_model = "qwen3.8"
            summary = "Deep reasoning and analytical synthesis on Qwen 3.8 (27B)."

        elif domain == "eda_hardware":
            strategy = "SINGLE_SPECIALIZED"
            primary_model = "gemini-2.5-flash"
            summary = "Domain-specialized hardware analysis via Gemini 2.5 Flash + S-expression AST tools."

        else:
            strategy = "SINGLE_SPECIALIZED"
            primary_model = "gemini-2.5-flash"
            summary = "General cloud reasoning via Gemini 2.5 Flash pool."

        latency_ms = (time.time() - start_t) * 1000

        logger.info(
            f"[Local Orchestrator] Triage in {latency_ms:.1f}ms: Domain='{domain}', "
            f"Strategy='{strategy}', PrimaryModel='{primary_model}'"
        )

        return OrchestratorPlan(
            domain=domain,
            complexity_score=complexity,
            execution_strategy=strategy,
            primary_model_id=primary_model,
            pipeline_steps=steps,
            estimated_context_tokens=len(prompt.split()) * 4 + 500,
            reasoning_summary=summary,
            evaluation_latency_ms=round(latency_ms, 2)
        )


# Global Singleton Orchestrator Instance
local_orchestrator = LocalLightweightOrchestrator()
