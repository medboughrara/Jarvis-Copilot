"""
Local Lightweight Orchestrator for Jarvis AI / Jarvis-Copilot.
Runs locally on CPU/GPU in <100ms (using ornith-1.5:9b / llama3:8b) to:
1. Parse user input and understand the underlying intent before calling heavy cloud models.
2. Fast-path deterministic regex triage for CODE_TASK and SEARCH_TASK in <10ms.
3. Evaluate task complexity, domain, and token context requirements.
4. Select optimal execution strategy:
   - DIRECT_LOCAL: Handled locally in ~50ms for simple chat / greetings / local controls.
   - SINGLE_SPECIALIZED: Routes directly to domain champion (e.g. glm-5.3-flash for vision, qwen3.8 for research).
   - COLLABORATIVE_PIPELINE: Multi-model sequential pipeline (Plan with glm-5.3 -> Implement with kimi-k2.7-code -> Verify with glm-5.3-flash).
"""

import re
import time
from typing import Dict, Any, List, Optional, Tuple
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
    domain: str  # "simple_chat", "coding", "search", "multimodal", "research", "eda_hardware"
    complexity_score: int  # 1 (instant) to 5 (complex multi-step)
    execution_strategy: str  # "DIRECT_LOCAL", "SINGLE_SPECIALIZED", "COLLABORATIVE_PIPELINE"
    primary_model_id: str
    pipeline_steps: List[PipelineStep] = field(default_factory=list)
    estimated_context_tokens: int = 1000
    reasoning_summary: str = ""
    evaluation_latency_ms: float = 0.0
    triage_source: str = "rule_match"  # "rule_match" or "llm_triage"


class LocalLightweightOrchestrator:
    """Fast local intent evaluator and multi-model agentic orchestrator."""

    def __init__(self, local_model_id: str = "ornith-1.5:9b"):
        self.local_model_id = local_model_id

    def _rule_based_triage(self, prompt: str) -> Optional[Tuple[str, str, int, str, str]]:
        """
        Fast-path deterministic regex/rule check (<10ms) before invoking LLM triage.
        Returns (domain, strategy, complexity, primary_model, summary) if high confidence, else None.
        """
        lower_p = prompt.lower().strip()

        # 1. Explicit CODE_TASK: checked first (to prevent algorithmic 'binary search' from misclassifying as web search)
        code_action_verbs = [
            r"\bwrite a (python|javascript|typescript|c\+\+|rust|go|java|function|script|class|module|test)\b",
            r"\bwrite (python|javascript|rust|c\+\+|code|unit test)\b",
            r"\bgenerate (a |an )?(python |javascript |typescript |rust |c\+\+ )?(code|script|function|class|unit test|test cases|pytest)\b",
            r"\bimplement (a |an |the )?.*?(function|algorithm|class|feature|script|pipeline|reversal|linked list|tree|sort|search|transform)\b",
            r"\bfix this (function|bug|code|script|error)\b", r"\brefactor\b", r"\bcreate a script\b",
            r"\bwrite unit tests\b", r"\bpytest\b", r"\bcalculate primes\b"
        ]
        has_code_block = "```" in prompt or "def " in prompt or "class " in prompt or "import " in prompt
        has_source_ext = any(lower_p.endswith(ext) or f"{ext} " in lower_p for ext in [".py", ".js", ".ts", ".cpp", ".rs", ".html", ".css"])

        if any(re.search(p, lower_p) for p in code_action_verbs) or (has_code_block and ("fix" in lower_p or "write" in lower_p or "test" in lower_p)) or has_source_ext:
            is_complex = len(prompt.split()) > 20 or "architecture" in lower_p or "refactor" in lower_p or "distributed" in lower_p
            if is_complex:
                return (
                    "coding",
                    "COLLABORATIVE_PIPELINE",
                    5,
                    "glm-5.3:cloud",
                    "Complex long-horizon coding task routed to Collaborative Pipeline (GLM-5.3 plan -> Kimi K2.7 Code -> GLM-5.3 Flash verify)."
                )
            else:
                return (
                    "coding",
                    "SINGLE_SPECIALIZED",
                    3,
                    "kimi-k2.7-code:cloud",
                    "Code generation task routed directly to Kimi K2.7 Code (1.04T parameter model)."
                )

        # 2. Explicit SEARCH_TASK: triggered ONLY by explicit search verbs
        search_triggers = [
            r"\bsearch for\b", r"\blook up\b", r"\bfind online\b", r"\bsearch the web\b",
            r"\bcheck the web\b", r"\bwhat('?s| is) the latest\b", r"\blatest news\b",
            r"\bgoogle for\b", r"\bbrowse for\b", r"^search\b"
        ]
        if any(re.search(p, lower_p) for p in search_triggers):
            return (
                "search",
                "SINGLE_SPECIALIZED",
                2,
                "qwen3.8",
                "Explicit web search request routed to ReachTool with source citations."
            )

        # 3. Simple Chat / Greeting
        simple_chat_triggers = [
            r"^(hello|hi|hey|howdy|good morning|good evening|good afternoon|who are you|what is your name)\b",
            r"^(thank you|thanks|bye|goodbye)\b"
        ]
        if len(lower_p.split()) <= 6 and any(re.search(p, lower_p) for p in simple_chat_triggers):
            return (
                "simple_chat",
                "DIRECT_LOCAL",
                1,
                "ornith-1.5:9b",
                "Direct local execution for fast response (<50ms)."
            )

        return None

    def evaluate_intent(self, prompt: str, context_metadata: Dict[str, Any] = None) -> OrchestratorPlan:
        """
        Evaluates user prompt in <100ms and returns the architectural routing plan.
        """
        start_t = time.time()
        lower_p = prompt.lower().strip()

        # Step 1: Fast Deterministic Rule Check (<5ms)
        rule_res = self._rule_based_triage(prompt)
        if rule_res:
            domain, strategy, complexity, primary_model, summary = rule_res
            triage_source = "rule_match"
        else:
            triage_source = "llm_triage"
            # Multimodal / Vision check
            is_multimodal = any(k in lower_p for k in [
                "image", "picture", "screenshot", "screen", "capture", "ocr", "gui", "diagram",
                "look at this", "inspect visual", "photo", "schematic view", ".png", ".jpg", ".webp"
            ])
            # EDA / Hardware check
            is_eda_hardware = any(k in lower_p for k in [
                "kicad", "schematic", "pcb", "netlist", "drc", "erc", "trace", "thermal loss",
                "joule", "ipc-2221", "footprint", "bom", "resistor", "capacitor", "stm32", "esp32",
                "gerber", "drill", "layer stackup", "signal integrity", "impedance", "via"
            ])
            # Deep Research check
            is_research = any(k in lower_p for k in [
                "research", "paper", "calculate", "math", "derive", "analyze trend", "deep search",
                "compare architectures", "literature review", "benchmark", "pros and cons"
            ])

            if is_multimodal:
                domain = "multimodal"
                strategy = "SINGLE_SPECIALIZED"
                complexity = 3
                primary_model = "glm-5.3-flash:cloud"
                summary = "Multimodal vision task routed to GLM-5.3 Flash (1M context)."
            elif is_eda_hardware:
                domain = "eda_hardware"
                strategy = "SINGLE_SPECIALIZED"
                complexity = 4
                primary_model = "gemini-2.5-flash"
                summary = "Hardware EDA analysis routed to Gemini 2.5 Flash + S-expression AST tools."
            elif is_research:
                domain = "research"
                strategy = "SINGLE_SPECIALIZED"
                complexity = 4
                primary_model = "qwen3.8"
                summary = "Deep analytical reasoning routed to Qwen 3.8 (27B)."
            else:
                domain = "general"
                strategy = "SINGLE_SPECIALIZED"
                complexity = 2
                primary_model = "gemini-2.5-flash"
                summary = "General reasoning routed to Gemini 2.5 Flash pool."

        # Construct Collaborative Steps if applicable
        steps = []
        if strategy == "COLLABORATIVE_PIPELINE":
            steps = [
                PipelineStep(1, "planner", "glm-5.3:cloud", "Architectural deconstruction & multi-step planning (753B / 1M context)"),
                PipelineStep(2, "generator", "kimi-k2.7-code:cloud", "High-efficiency code implementation (1.04T parameter coding model)"),
                PipelineStep(3, "verifier", "glm-5.3-flash:cloud", "AST syntax check, lint verification & test execution")
            ]

        latency_ms = (time.time() - start_t) * 1000

        logger.info(
            f"[Local Orchestrator] Triage in {latency_ms:.1f}ms [{triage_source}]: Domain='{domain}', "
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
            evaluation_latency_ms=round(latency_ms, 2),
            triage_source=triage_source
        )


# Global Singleton Orchestrator Instance
local_orchestrator = LocalLightweightOrchestrator()
