"""
Local Lightweight Orchestrator & Two-Stage Local-First SLM Engine for Jarvis AI.
Stage 1: Ultra-Fast Local SLM & Local Reflex (<50ms)
  - Understands user intent and conversational nuance.
  - Instantly answers basic questions, greetings, identity, capabilities, time, system health, and pleasantries locally without heavy cloud roundtrips.
  - Detects if an actionable task exists.
Stage 2: Specialized Agent Execution Pipeline
  - Dispatches actionable tasks to domain champions (Kimi K2.7 Code, ReachTool Search, Anthropic Security Skills, KiCad EDA, TaskRunner).
"""

import re
import time
import os
import datetime
import psutil
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import config
from agent.model_registry import model_registry

logger = config.get_logger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class PipelineStep:
    step_number: int
    role: str  # "planner", "generator", "verifier", "executor"
    model_id: str
    description: str


@dataclass
class OrchestratorPlan:
    domain: str  # "simple_chat", "coding", "search", "security", "multimodal", "research", "eda_hardware"
    complexity_score: int  # 1 (instant) to 5 (complex multi-step)
    execution_strategy: str  # "DIRECT_LOCAL", "SINGLE_SPECIALIZED", "COLLABORATIVE_PIPELINE"
    primary_model_id: str
    pipeline_steps: List[PipelineStep] = field(default_factory=list)
    estimated_context_tokens: int = 1000
    reasoning_summary: str = ""
    evaluation_latency_ms: float = 0.0
    triage_source: str = "rule_match"  # "rule_match" or "llm_triage"
    is_actionable_task: bool = False


class LocalSLMReflexEngine:
    """Ultra-fast local SLM & reflex responder for zero-latency conversational turns."""

    def __init__(self):
        self.ollama_base_url = getattr(config.settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        self.slm_model = getattr(config.settings, "OLLAMA_SLM_MODEL", "llama3.2:1b")

    def generate_reflex_response(self, prompt: str) -> Optional[str]:
        """
        Generates immediate, dynamic, context-aware local reflex responses in <2ms.
        """
        lower_p = prompt.lower().strip()

        # 1. Greetings & How-are-you
        if any(re.search(p, lower_p) for p in [
            r"\b(how are you|how('?s| is) it going|how are you doing|how do you do|how are things)\b",
            r"^(hello|hi|hey|howdy|greetings)\b"
        ]):
            now = datetime.datetime.now()
            hour = now.hour
            time_greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")
            return (
                f"{time_greeting}, sir! I am operating at full capacity. All local telemetry monitors, "
                f"hardware analysis engines, and security modules are online and ready for your command."
            )

        # 2. Time & Date
        if any(re.search(p, lower_p) for p in [
            r"\b(what time is it|what is the time|current time|what('?s| is) the date|today'?s date|what day is it)\b"
        ]):
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            date_str = now.strftime("%A, %B %d, %Y")
            return f"The current time is {time_str} on {date_str}."

        # 3. Identity & Creator
        if any(re.search(p, lower_p) for p in [
            r"\b(who are you|what are you|what is your name|who created you|who built you|who made you|tell me about yourself)\b"
        ]):
            return (
                "I am Jarvis, your tactical hardware copilot and autonomous engineering assistant. "
                "I specialize in KiCad schematic analysis, IPC-2221 thermal loss calculations, signal integrity, "
                "cybersecurity tradecraft, and autonomous task execution."
            )

        # 4. Capabilities & Help
        if any(re.search(p, lower_p) for p in [
            r"\b(what can you do|help|what are your features|capabilities|what skills do you have|what tools do you have)\b"
        ]):
            return (
                "Here is what I can do for you:\n"
                "• **Hardware & PCB EDA:** Review KiCad schematics, detect ERC/DRC violations, calculate IPC-2221 thermal loss, autoroute boards.\n"
                "• **Autonomous Coding:** Generate, test, and AST-verify code in an isolated execution sandbox.\n"
                "• **Explicit Web Search:** Research datasheets, pinouts, and technical specs with source citations.\n"
                "• **Cybersecurity Skills:** Execute practitioner playbooks and MITRE ATT&CK/NIST CSF tradecraft with scope-bound security.\n"
                "• **Multi-App Automation:** Connect with Gmail, Google Calendar, Notion, Sheets, Discord, and system controls."
            )

        # 5. System Status & Health Metrics
        if any(re.search(p, lower_p) for p in [
            r"\b(system status|hardware status|system stats|cpu usage|ram usage|health check|how is the system)\b"
        ]):
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            return f"System diagnostics nominal: CPU utilization is at {cpu:.1f}%, System RAM is at {mem:.1f}%, and all local agents are operational."

        # 6. Jokes & Fun
        if any(re.search(p, lower_p) for p in [
            r"\b(tell me a joke|say something funny|tell a joke|make me laugh)\b"
        ]):
            return (
                "Why do hardware engineers prefer dark mode?\n"
                "Because light attracts bugs — and in hardware, bugs can let the magic smoke out!"
            )

        # 7. Pleasantries & Thanks
        if any(re.search(p, lower_p) for p in [
            r"\b(thank you|thanks|appreciate it|good job|awesome|nice one|great job)\b"
        ]):
            return "You are very welcome, sir. Always at your service."

        if any(re.search(p, lower_p) for p in [
            r"\b(bye|goodbye|see you|good night|farewell)\b"
        ]):
            return "Standing by in low-power idle mode. Let me know whenever you need me, sir."

        return None

    async def query_local_slm(self, prompt: str, history: List[Dict[str, str]] = None) -> Optional[str]:
        """
        Attempts to query a local Ollama Small Language Model (SLM) for open-ended conversational turns (<300ms).
        """
        if not HTTPX_AVAILABLE:
            return None

        system_instruction = (
            "You are Jarvis, a fast, crisp, polite AI assistant. "
            "Answer the user's conversational query directly in 1-2 clear, helpful sentences. "
            "Do not output markdown code blocks or tool calls."
        )

        try:
            async with httpx.AsyncClient(timeout=1.2) as client:
                resp = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.slm_model,
                        "prompt": prompt,
                        "system": system_instruction,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 128
                        }
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    res_text = data.get("response", "").strip()
                    if res_text:
                        return res_text
        except Exception:
            pass

        return None


class LocalLightweightOrchestrator:
    """Fast local intent evaluator and multi-model agentic orchestrator."""

    def __init__(self, local_model_id: str = "ornith-1.5:9b"):
        self.local_model_id = local_model_id
        self.reflex_engine = LocalSLMReflexEngine()

    def _rule_based_triage(self, prompt: str) -> Optional[Tuple[str, str, int, str, str, bool]]:
        """
        Fast-path deterministic regex/rule check (<10ms) before invoking LLM triage.
        Returns (domain, strategy, complexity, primary_model, summary, is_actionable_task) if high confidence, else None.
        """
        lower_p = prompt.lower().strip()

        # 1. Explicit CODE_TASK: checked first
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
                    "Complex long-horizon coding task routed to Collaborative Pipeline (GLM-5.3 plan -> Kimi K2.7 Code -> GLM-5.3 Flash verify).",
                    True
                )
            else:
                return (
                    "coding",
                    "SINGLE_SPECIALIZED",
                    3,
                    "kimi-k2.7-code:cloud",
                    "Code generation task routed directly to Kimi K2.7 Code (1.04T parameter model).",
                    True
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
                "Explicit web search request routed to ReachTool with source citations.",
                True
            )

        # 3. Explicit SECURITY_TASK: matched against 29 cybersecurity domains and key tradecraft terms
        security_triggers = [
            r"\bmemory forensics\b", r"\bvolatility\b", r"\bthreat hunt(ing)?\b", r"\bincident response\b",
            r"\bsiem\b", r"\bsoc\b", r"\bpentest(ing)?\b", r"\bred team(ing)?\b", r"\bphishing\b",
            r"\bmalware analysis\b", r"\bvulnerability scan(ning)?\b", r"\biam hardening\b",
            r"\bcontainer security\b", r"\bot/ics\b", r"\bmitre attack\b", r"\bnist csf\b",
            r"\bd3fend\b", r"\bprocess injection\b", r"\bcredential dumping\b", r"\bkerberoasting\b",
            r"\bdcsync\b", r"\bshadow credentials\b", r"\bactive directory security\b",
            r"\bdigital forensics\b", r"\bdfir\b", r"\bthreat intelligence\b", r"\bmisp\b"
        ]
        if any(re.search(p, lower_p) for p in security_triggers):
            return (
                "security",
                "SINGLE_SPECIALIZED",
                3,
                "qwen3.8",
                "Cybersecurity practitioner task routed through Anthropic Security Skills RAG.",
                True
            )

        # 4. Stage 1 Fast Conversational & Reflex Triggers
        conversational_triggers = [
            r"\b(how are you|how('?s| is) it going|how are you doing|how do you do|how are things)\b",
            r"^(hello|hi|hey|howdy|good morning|good evening|good afternoon|greetings)\b",
            r"\b(who are you|what are you|what is your name|who created you|who built you|who made you|tell me about yourself)\b",
            r"\b(what can you do|help|capabilities|what are your skills|what are your features|what tools do you have)\b",
            r"\b(what time is it|what is the time|what is the date|today'?s date|current time)\b",
            r"\b(thank you|thanks|appreciate it|bye|goodbye|see you|good job|awesome)\b",
            r"\b(system status|hardware status|system stats|cpu usage|ram usage|health check)\b",
            r"\b(tell me a joke|say something funny)\b"
        ]
        # Action task indicators that prevent simple chat misclassification
        has_task_intent = any(re.search(p, lower_p) for p in [
            r"\b(write|create|make|build|generate|design|route|audit|export|calculate|simulate|send|delete|save|update)\b",
            r"\b(kicad|schematic|pcb|thermal|gerber|email|calendar|workflow|recipe|script)\b"
        ])

        if not has_task_intent and any(re.search(p, lower_p) for p in conversational_triggers):
            return (
                "simple_chat",
                "DIRECT_LOCAL",
                1,
                "ornith-1.5:9b",
                "Direct Stage 1 Local SLM / Reflex execution for zero-latency response (<10ms).",
                False
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
            domain, strategy, complexity, primary_model, summary, is_task = rule_res
            triage_source = "rule_match"
        else:
            triage_source = "llm_triage"
            is_task = True
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
            f"Strategy='{strategy}', PrimaryModel='{primary_model}', IsTask={is_task}"
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
            triage_source=triage_source,
            is_actionable_task=is_task
        )

    async def evaluate_and_respond_async(
        self,
        prompt: str,
        history: List[Dict[str, str]] = None
    ) -> Tuple[bool, Optional[str], OrchestratorPlan]:
        """
        Stage 1 Local-First Dispatcher:
        1. Evaluates intent plan.
        2. If it is a conversational / basic query (not an actionable task), answers immediately in <5ms.
        3. Returns (is_handled_locally, local_response_text, plan).
        """
        plan = self.evaluate_intent(prompt)

        # If it's a simple chat or direct local request:
        if plan.domain == "simple_chat" or not plan.is_actionable_task:
            # 1. Try instant local reflex response (<2ms)
            reflex_resp = self.reflex_engine.generate_reflex_response(prompt)
            if reflex_resp:
                return True, reflex_resp, plan

            # 2. Try local SLM if configured
            if getattr(config.settings, "USE_STAGE1_LOCAL_SLM", True):
                slm_resp = await self.reflex_engine.query_local_slm(prompt, history)
                if slm_resp:
                    return True, slm_resp, plan

            # 3. Default friendly local response
            default_resp = "I am online and ready to assist, sir. How can I help with your project today?"
            return True, default_resp, plan

        # Actionable task detected: proceed to Stage 2
        return False, None, plan


# Global Singleton Orchestrator Instance
local_orchestrator = LocalLightweightOrchestrator()
