"""
LangChain Copilot Agent Initialization for Jarvis PCB Copilot.
Combines local ChatOllama (GPU RTX 3050 target) with KiCad, agent-reach, and OmniParser V2 tools.
Supports Conversation History Memory & Context Consciousness for follow-up engineering questions.
"""

import asyncio
from typing import List, Dict, Optional
import config
from agent.prompts import JARVIS_SYSTEM_PROMPT
from agent.key_manager import GeminiKeyManager
from agent.skill_loader import SkillLoader
from agent.session_context import JarvisSessionContext
from agent.composio_router import ComposioRouter
from agent.workflows import run_full_pcb_audit
from tools.formatters import format_tool_output_for_cli, format_tool_output_for_voice
from tools.kicad_tool import analyze_kicad_file, get_power_tree, check_pcb_errors, generate_bom_report
from tools.reach_tool import search_component_datasheet, check_compliance_status
from tools.omniparser_tool import parse_screen_gui
from tools.datasheet_rag_tool import query_local_datasheets
from tools.thermal_tool import calculate_thermal_loss
from tools.signal_integrity_tool import check_signal_integrity
from tools.supply_chain_tool import check_supply_chain_status
from tools.github_tool import manage_github_issue
from tools.doc_exporter_tool import export_engineering_doc
from tools.nvidia_nim_tool import (
    generate_nvidia_image,
    synthesize_nvidia_speech,
    transcribe_nvidia_audio,
    run_nvidia_reasoning,
    parse_nemotron_ocr,
    NvidiaNIMClient
)
from tools.unlimited_ocr_tool import parse_document_unlimited_ocr

logger = config.get_logger(__name__)

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGCHAIN_GEMINI_AVAILABLE = True
except ImportError:
    LANGCHAIN_GEMINI_AVAILABLE = False

try:
    from langchain_ollama import ChatOllama
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    LANGCHAIN_OLLAMA_AVAILABLE = True
except ImportError:
    LANGCHAIN_OLLAMA_AVAILABLE = False


class JarvisAgent:
    def __init__(self, model_name: str = config.OLLAMA_MODEL, base_url: str = config.OLLAMA_BASE_URL, session_context: Optional[JarvisSessionContext] = None):
        self.model_name = model_name
        self.base_url = base_url
        self.session_context = session_context or JarvisSessionContext()
        self.skill_loader = SkillLoader()

        # Registered PCB Copilot Tools
        self.tools = [
            analyze_kicad_file,
            get_power_tree,
            check_pcb_errors,
            generate_bom_report,
            search_component_datasheet,
            check_compliance_status,
            parse_screen_gui,
            query_local_datasheets,
            calculate_thermal_loss,
            check_signal_integrity,
            check_supply_chain_status,
            manage_github_issue,
            export_engineering_doc,
            generate_nvidia_image,
            synthesize_nvidia_speech,
            transcribe_nvidia_audio,
            run_nvidia_reasoning,
            parse_nemotron_ocr,
            parse_document_unlimited_ocr
        ]
        self.composio_router = ComposioRouter(self.tools)
        self.tools_by_name = {t.name: t for t in self.tools}
        self.llm_with_tools = None
        self.raw_llm = None
        self.ollama_llm = None
        self.history: List[Dict[str, str]] = []
        self.last_tool_context: str = ""

        # Multi-Key Gemini Engine Pool Initialization
        self.key_manager = GeminiKeyManager()

    async def process_query(self, user_query: str) -> str:
        """
        Processes query through tool router, multi-tier LLM fallback pipeline, and updates memory.
        """
        lower_q = user_query.lower()
        tool_executed = False
        tool_result = ""

        # Direct Keyword Intent Dispatcher
        if "analyze" in lower_q or "schematic" in lower_q or "kicad file" in lower_q:
            tool_result = analyze_kicad_file.invoke({"file_path": ""})
            tool_executed = True
        elif "power tree" in lower_q or "power map" in lower_q or "voltage rails" in lower_q:
            tool_result = get_power_tree.invoke({"file_path": ""})
            tool_executed = True
        elif "check errors" in lower_q or "erc" in lower_q or "drc" in lower_q or "rules check" in lower_q or "floating" in lower_q:
            tool_result = check_pcb_errors.invoke({"file_path": ""})
            tool_executed = True
        elif "bom" in lower_q or "bill of materials" in lower_q or "parts list" in lower_q:
            tool_result = generate_bom_report.invoke({"file_path": ""})
            tool_executed = True
        elif "thermal" in lower_q or "trace width" in lower_q or "heat" in lower_q or "ipc-2221" in lower_q:
            tool_result = calculate_thermal_loss.invoke({})
            tool_executed = True
        elif "signal integrity" in lower_q or "i2c pullup" in lower_q or "pull-up" in lower_q or "impedance" in lower_q:
            tool_result = check_signal_integrity.invoke({"bus_type": "i2c"})
            tool_executed = True
        elif "supply chain" in lower_q or "lifecycle" in lower_q or "stock" in lower_q or "obsolescence" in lower_q:
            tool_result = check_supply_chain_status.invoke({"part_number": "STM32F405RGT6"})
            tool_executed = True
        elif "rohs" in lower_q or "fcc" in lower_q or "compliance" in lower_q:
            tool_result = check_compliance_status.invoke({"component_name": "PCA9685"})
            tool_executed = True
        elif "datasheet" in lower_q or "specs" in lower_q:
            tool_result = search_component_datasheet.invoke({"query": user_query})
            tool_executed = True
        elif "screen" in lower_q or "capture" in lower_q or "gui" in lower_q or "omniparser" in lower_q:
            tool_result = parse_screen_gui.invoke({"action_context": user_query})
            tool_executed = True
        elif "rag" in lower_q or "local datasheet" in lower_q or "pdf search" in lower_q:
            tool_result = query_local_datasheets.invoke({"query": user_query})
            tool_executed = True
        elif "issue" in lower_q or "github" in lower_q or "log bug" in lower_q:
            tool_result = manage_github_issue.invoke({"title": "PCB Audit Finding", "body": user_query})
            tool_executed = True
        elif "export" in lower_q or "document" in lower_q or "doc" in lower_q:
            tool_result = export_engineering_doc.invoke({"title": "Engineering Review", "content": user_query})
            tool_executed = True
        elif "generate image" in lower_q or "flux" in lower_q or "artwork" in lower_q or "diagram" in lower_q:
            tool_result = generate_nvidia_image.invoke({"prompt": user_query})
            tool_executed = True
        elif "nvidia speech" in lower_q or "magpie" in lower_q or "tts" in lower_q:
            tool_result = synthesize_nvidia_speech.invoke({"text": user_query})
            tool_executed = True
        elif "reasoning" in lower_q or "kimi" in lower_q or "nemotron reasoning" in lower_q:
            tool_result = run_nvidia_reasoning.invoke({"query": user_query})
            tool_executed = True
        elif "nemotron ocr" in lower_q or "visual ocr" in lower_q:
            tool_result = parse_nemotron_ocr.invoke({"image_path": ""})
            tool_executed = True
        elif "unlimited ocr" in lower_q or "parse pdf" in lower_q or "baidu ocr" in lower_q:
            tool_result = parse_document_unlimited_ocr.invoke({"document_path": ""})
            tool_executed = True
        elif "api key" in lower_q or "key stat" in lower_q or "key tracking" in lower_q:
            tool_result = self.key_manager.get_usage_summary()
            logger.info(f"\n{tool_result}\n")
            tool_executed = True

        if tool_executed:
            self.last_tool_context = format_tool_output_for_cli(tool_result) if isinstance(tool_result, dict) else str(tool_result)

        messages = [SystemMessage(content=JARVIS_SYSTEM_PROMPT)]

        skill_prompt = self.skill_loader.get_skill_instructions(user_query)
        if skill_prompt:
            messages.append(SystemMessage(content=f"SKILL PLAYBOOK INSTRUCTIONS:\n{skill_prompt}"))

        scoped_tools = self.composio_router.filter_tools_for_query(user_query)

        if self.last_tool_context:
            context_msg = f"ACTIVE SYSTEM/TOOL CONTEXT:\n{self.last_tool_context}\n\nPlease synthesize this data naturally into your conversational response."
            messages.append(SystemMessage(content=context_msg))

        for item in self.history[-8:]:
            if item["role"] == "user":
                messages.append(HumanMessage(content=item["content"]))
            else:
                messages.append(AIMessage(content=item["content"]))

        messages.append(HumanMessage(content=user_query))

        response = None

        # Tier 1: Multi-Key Google Gemini Pool
        if getattr(config, 'USE_GEMINI', False) and LANGCHAIN_GEMINI_AVAILABLE and self.key_manager.api_keys:
            max_attempts = len(self.key_manager.api_keys)
            for attempt in range(max_attempts):
                working_key = self.key_manager.get_working_key()
                if not working_key:
                    logger.warning("[Agent Key Manager] All Gemini API keys are currently rate-limited.")
                    break

                try:
                    gemini_model = ChatGoogleGenerativeAI(
                        model=config.GEMINI_MODEL,
                        api_key=working_key,
                        temperature=0.3
                    )
                    if scoped_tools and hasattr(gemini_model, 'bind_tools'):
                        gemini_model = gemini_model.bind_tools(scoped_tools)
                    response = await gemini_model.ainvoke(messages)
                    self.key_manager.report_success(working_key)
                    break
                except Exception as e:
                    err_msg = str(e)
                    is_rate_limit = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Quota" in err_msg
                    self.key_manager.report_error(working_key, is_rate_limit=is_rate_limit, cooldown_seconds=60)
                    logger.warning(f"[Agent Key Manager] Gemini key error ({e}). Auto-rotating to next key...")

        # Tier 2: NVIDIA NIM Cloud Reasoning Tier
        if not response and (getattr(config, 'NVIDIA_KIMI_KEY', '') or getattr(config, 'NVIDIA_NEMOTRON_KEY', '')):
            nim_models = []
            if config.NVIDIA_KIMI_KEY:
                nim_models.append(("moonshotai/kimi-k2.6", config.NVIDIA_KIMI_KEY))
            if config.NVIDIA_NEMOTRON_KEY:
                nim_models.append(("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", config.NVIDIA_NEMOTRON_KEY))

            for n_model, n_key in nim_models:
                logger.info(f"[Agent Fallback] Attempting NVIDIA NIM Model '{n_model}'...")
                try:
                    client = NvidiaNIMClient(api_key=n_key)
                    query_text = messages[-1].content
                    reasoning_out = client.invoke_chat_completion(
                        messages=[{"role": "user", "content": query_text}],
                        model=n_model
                    )
                    if reasoning_out and not reasoning_out.startswith("[Error"):
                        response = AIMessage(content=reasoning_out)
                        break
                except Exception as ne:
                    logger.warning(f"[NVIDIA NIM Fallback Failed for {n_model}]: {ne}")

        # Tier 3: Local Ollama
        if not response and LANGCHAIN_OLLAMA_AVAILABLE:
            logger.info(f"[Agent Fallback] Routing query to Local Ollama ({self.model_name})...")
            try:
                self.ollama_llm = ChatOllama(model=self.model_name, base_url=self.base_url, temperature=0.3)
                if scoped_tools and hasattr(self.ollama_llm, 'bind_tools'):
                    self.ollama_llm = self.ollama_llm.bind_tools(scoped_tools)
                response = await self.ollama_llm.ainvoke(messages)
            except Exception as oe:
                logger.error(f"[Local Ollama Execution Error]: {oe}")

        # Fallback text if LLM models offline
        final_answer = ""
        if response:
            if hasattr(response, 'content') and isinstance(response.content, str):
                final_answer = response.content
            elif hasattr(response, 'content') and isinstance(response.content, list):
                text_parts = [c.get("text", "") for c in response.content if isinstance(c, dict) and "text" in c]
                final_answer = "\n".join(text_parts) if text_parts else str(response.content)
            else:
                final_answer = str(response)
        else:
            if tool_executed:
                final_answer = f"I executed the tool analysis for you:\n\n{self.last_tool_context}"
            else:
                final_answer = "I am ready to assist with your KiCad PCB design and servomotor requirements."

        self.history.append({"role": "user", "content": user_query})
        self.history.append({"role": "assistant", "content": final_answer})

        return final_answer
