"""
LangChain Copilot Agent Initialization for Jarvis PCB Copilot.
Combines local ChatOllama (GPU RTX 3050 target) with KiCad, agent-reach, and OmniParser V2 tools.
Supports Conversation History Memory & Context Consciousness for follow-up engineering questions.
"""

import asyncio
from typing import List, Dict
import config
from agent.prompts import JARVIS_SYSTEM_PROMPT
from agent.key_manager import GeminiKeyManager
from agent.skill_loader import SkillLoader
from agent.composio_router import ComposioRouter
from agent.workflows import run_full_pcb_audit
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
    def __init__(self, model_name: str = config.OLLAMA_MODEL, base_url: str = config.OLLAMA_BASE_URL):
        self.model_name = model_name
        self.base_url = base_url
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
            parse_nemotron_ocr
        ]
        self.composio_router = ComposioRouter(self.tools)
        self.tools_by_name = {t.name: t for t in self.tools}
        self.llm_with_tools = None
        self.raw_llm = None
        self.ollama_llm = None

        # Context Consciousness Memory
        self.history: List[Dict[str, str]] = []  # List of {"role": "user"|"assistant", "content": text}
        self.last_tool_context: str = ""        # Context cache of last executed tool output (e.g. screen analysis, power tree)

        # Gemini Multi-Key Rotation & Tracking Manager
        self.key_manager = GeminiKeyManager()

        # Initialize secondary local Ollama fallback engine
        if LANGCHAIN_OLLAMA_AVAILABLE:
            try:
                self.ollama_llm = ChatOllama(
                    model=self.model_name,
                    base_url=self.base_url,
                    temperature=0.3
                )
            except Exception as oe:
                print(f"[Agent Warning] ChatOllama fallback init notice: {oe}")
                self.ollama_llm = None

        # Initialize primary Google Gemini engine notice
        if getattr(config, 'USE_GEMINI', False) and LANGCHAIN_GEMINI_AVAILABLE and self.key_manager.api_keys:
            print(f"[Agent Memory] Initializing Multi-Key Gemini Engine ({config.GEMINI_MODEL}) with {len(self.key_manager.api_keys)} registered keys...")
            print(self.key_manager.get_usage_summary())
        elif self.ollama_llm:
            print(f"[Agent Memory] Active Engine: ChatOllama ({self.model_name} at {self.base_url})")
        else:
            print("[Agent Warning] No active LLM engine loaded (neither Gemini nor Ollama).")

    def _save_turn(self, user_query: str, assistant_response: str):
        """Saves interaction turn to conversation history memory (max 10 turns)."""
        self.history.append({"role": "user", "content": user_query})
        self.history.append({"role": "assistant", "content": assistant_response})
        if len(self.history) > 20:  # 10 turns (20 messages)
            self.history = self.history[-20:]

    async def process_query(self, user_query: str) -> str:
        """
        Processes user query through LangChain agent, retaining conversation memory context for follow-up questions.
        """
        if not user_query or not user_query.strip():
            return "I didn't catch that. Could you please repeat?"

        print(f"\n[Agent Input] AutoPick Query: '{user_query}'")

        # 1. Smart Keyword Tool Dispatcher
        lower_q = user_query.lower()
        tool_executed = False
        tool_result = ""

        if "screen" in lower_q or "gui" in lower_q or "omniparser" in lower_q or "capture my screen" in lower_q:
            tool_result = parse_screen_gui.invoke({"action_context": user_query})
            tool_executed = True
        elif "power tree" in lower_q or "power distribution" in lower_q:
            tool_result = get_power_tree.invoke({"file_path": ""})
            tool_executed = True
        elif "bom" in lower_q or "bill of materials" in lower_q:
            tool_result = generate_bom_report.invoke({"file_path": ""})
            tool_executed = True
        elif "datasheet" in lower_q or "sts" in lower_q or ("servo" in lower_q and "rohs" not in lower_q and "fcc" not in lower_q):
            tool_result = search_component_datasheet.invoke({"query": user_query})
            tool_executed = True
        elif "rohs" in lower_q or "fcc" in lower_q or "compliance" in lower_q:
            tool_result = check_compliance_status.invoke({"component_name": user_query})
            tool_executed = True
        elif "erc" in lower_q or "drc" in lower_q or "schematic check" in lower_q:
            tool_result = check_pcb_errors.invoke({"file_path": ""})
            tool_executed = True
        elif "what can you do" in lower_q or "help" in lower_q or "commands" in lower_q:
            tool_result = "I am Jarvis, your PCB Copilot. I can analyze your KiCad schematics, generate power distribution trees, run ERC checks, create Bill of Materials, look up component datasheets, verify RoHS and FCC compliance, and even analyze your active screen."
            tool_executed = True
        elif "local datasheet" in lower_q or "local pdf" in lower_q or "document" in lower_q or "rag" in lower_q:
            tool_result = query_local_datasheets.invoke({"query": user_query})
            tool_executed = True
        elif "thermal" in lower_q or "heat" in lower_q or "power loss" in lower_q or "ipc" in lower_q:
            tool_result = calculate_thermal_loss.invoke({})
            tool_executed = True
        elif "signal integrity" in lower_q or "pullup" in lower_q or "impedance" in lower_q or "termination" in lower_q:
            tool_result = check_signal_integrity.invoke({"bus_type": "i2c"})
            tool_executed = True
        elif "supply chain" in lower_q or "obsolescence" in lower_q or "stock" in lower_q or "lifecycle" in lower_q:
            tool_result = check_supply_chain_status.invoke({"part_number": user_query})
            tool_executed = True
        elif "audit workflow" in lower_q or "full audit" in lower_q or "run workflow" in lower_q or "pcb audit" in lower_q:
            res = run_full_pcb_audit("")
            tool_result = f"Full PCB Audit completed! Executive summary: {res['summary']}. Report written to scratch/pcb_audit_report.md"
            tool_executed = True
        elif "skills" in lower_q or "playbook" in lower_q or "capabilities" in lower_q:
            tool_result = self.skill_loader.list_skills_summary()
            tool_executed = True
        elif "github" in lower_q or "log issue" in lower_q or "create issue" in lower_q:
            tool_result = manage_github_issue.invoke({"title": "AutoPick Schematic Review Item", "body": user_query, "labels": "hardware-erc"})
            tool_executed = True
        elif "export" in lower_q or "save log" in lower_q or "doc" in lower_q:
            tool_result = export_engineering_doc.invoke({"title": "AutoPick Engineering Review", "content": user_query})
            tool_executed = True
        elif "generate image" in lower_q or "flux" in lower_q or "nvidia image" in lower_q or "draw" in lower_q or "visualize concept" in lower_q:
            tool_result = generate_nvidia_image.invoke({"prompt": user_query})
            tool_executed = True
        elif "api key" in lower_q or "key stat" in lower_q or "key tracking" in lower_q or "gemini usage" in lower_q or "quota status" in lower_q:
            tool_result = self.key_manager.get_usage_summary()
            print(f"\n{tool_result}\n")
            tool_executed = True

        if tool_executed:
            self.last_tool_context = tool_result
            # We no longer return early here. We let the LLM synthesize the raw tool output.

        # 2. Build Memory & Context Aware Prompt Messages for Ollama LLM
        messages = [SystemMessage(content=JARVIS_SYSTEM_PROMPT)]

        # Append dynamic SKILL.md playbook instructions if relevant
        skill_prompt = self.skill_loader.get_skill_instructions(user_query)
        if skill_prompt:
            messages.append(SystemMessage(content=f"SKILL PLAYBOOK INSTRUCTIONS:\n{skill_prompt}"))

        # Filter tools for query using ComposioRouter
        scoped_tools = self.composio_router.filter_tools_for_query(user_query)

        # Append active tool context if available (e.g. freshly captured screen circuit, power tree, or search result)
        if self.last_tool_context:
            context_msg = f"ACTIVE SYSTEM/TOOL CONTEXT:\n{self.last_tool_context}\n\nPlease synthesize this data naturally into your conversational response."
            messages.append(SystemMessage(content=context_msg))

        # Append conversation history turns
        for item in self.history[-8:]:  # Last 4 turns
            if item["role"] == "user":
                messages.append(HumanMessage(content=item["content"]))
            else:
                messages.append(AIMessage(content=item["content"]))

        # Append current user query
        messages.append(HumanMessage(content=user_query))

        # 3. Hierarchical Multi-Tier LLM Execution & Fallback Pipeline
        # Tier 1: Multi-Key Google Gemini Pool (Round-robin + 429 auto-cooling)
        # Tier 2: Ollama Cloud Models (glm-5.2:cloud, kimi-k3:cloud)
        # Tier 3: Local Ollama Model (llama3:8b)

        response = None

        # Tier 1: Google Gemini API Keys
        if getattr(config, 'USE_GEMINI', False) and LANGCHAIN_GEMINI_AVAILABLE and self.key_manager.api_keys:
            max_attempts = len(self.key_manager.api_keys)
            for attempt in range(max_attempts):
                working_key = self.key_manager.get_working_key()
                if not working_key:
                    print("[Agent Key Manager] All Gemini API keys are currently rate-limited.")
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
                    break  # Successful response!
                except Exception as e:
                    err_msg = str(e)
                    is_rate_limit = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Quota" in err_msg
                    self.key_manager.report_error(working_key, is_rate_limit=is_rate_limit, cooldown_seconds=60)
                    print(f"[Agent Key Manager] Gemini key error ({e}). Auto-rotating to next key...")

        # Tier 2: NVIDIA NIM Cloud Reasoning Tier (Kimi 2.6 & Nemotron 3 Reasoning)
        if not response and (getattr(config, 'NVIDIA_KIMI_KEY', '') or getattr(config, 'NVIDIA_NEMOTRON_KEY', '')):
            nim_models = []
            if config.NVIDIA_KIMI_KEY:
                nim_models.append(("moonshotai/kimi-k2.6", config.NVIDIA_KIMI_KEY))
            if config.NVIDIA_NEMOTRON_KEY:
                nim_models.append(("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", config.NVIDIA_NEMOTRON_KEY))

            for n_model, n_key in nim_models:
                print(f"[Agent Fallback] Attempting NVIDIA NIM Model '{n_model}'...")
                try:
                    client = NvidiaNIMClient(api_key=n_key)
                    nim_msg = [{"role": "system", "content": JARVIS_SYSTEM_PROMPT}]
                    if self.last_tool_context:
                        nim_msg.append({"role": "system", "content": f"TOOL CONTEXT:\n{self.last_tool_context}"})
                    nim_msg.append({"role": "user", "content": user_query})
                    
                    res_text = client.invoke_chat_completion(messages=nim_msg, model=n_model, api_key=n_key)
                    if res_text and not res_text.startswith("[Error"):
                        response = AIMessage(content=res_text)
                        print(f"[Agent Fallback] Success with NVIDIA NIM Model '{n_model}'.")
                        break
                except Exception as n_err:
                    print(f"[Agent Notice] NVIDIA NIM Model '{n_model}' error ({n_err}). Trying next...")

        # Tier 3: Ollama Cloud Models (glm-5.2:cloud, kimi-k3:cloud)
        if not response and LANGCHAIN_OLLAMA_AVAILABLE and getattr(config, 'OLLAMA_CLOUD_MODELS', []):
            for cloud_model in config.OLLAMA_CLOUD_MODELS:
                print(f"[Agent Fallback] Attempting Ollama Cloud Model '{cloud_model}'...")
                try:
                    ollama_cloud_engine = ChatOllama(
                        model=cloud_model,
                        base_url=self.base_url,
                        temperature=0.3
                    )
                    if scoped_tools and hasattr(ollama_cloud_engine, 'bind_tools'):
                        ollama_cloud_engine = ollama_cloud_engine.bind_tools(scoped_tools)
                    response = await ollama_cloud_engine.ainvoke(messages)
                    print(f"[Agent Fallback] Success with Ollama Cloud Model '{cloud_model}'.")
                    break
                except Exception as oce:
                    print(f"[Agent Notice] Ollama Cloud Model '{cloud_model}' unavailable ({oce}). Trying next...")

        # Tier 3: Local Ollama Model (llama3:8b)
        if not response and self.ollama_llm:
            print(f"[Agent Fallback] Invoking local ChatOllama model ({config.OLLAMA_MODEL})...")
            try:
                model_to_use = self.ollama_llm
                if scoped_tools and hasattr(model_to_use, 'bind_tools'):
                    model_to_use = model_to_use.bind_tools(scoped_tools)
                response = await model_to_use.ainvoke(messages)
            except Exception as oe:
                print(f"[Agent Ollama Local Fallback Error] {oe}")

        # Execute any tool calls generated by LLM tool binding
        if response and hasattr(response, 'tool_calls') and response.tool_calls:
            tool_outputs = []
            for tool_call in response.tool_calls:
                t_name = tool_call.get('name', '').lower()
                t_args = tool_call.get('args', {})
                # Find matching tool in self.tools_by_name (case insensitive match)
                matched_tool = None
                for registered_name, t_obj in self.tools_by_name.items():
                    if registered_name.lower() == t_name:
                        matched_tool = t_obj
                        break

                if matched_tool:
                    try:
                        res = matched_tool.invoke(t_args)
                        tool_outputs.append(str(res))
                    except Exception as te:
                        tool_outputs.append(f"Tool {t_name} error: {te}")
            if tool_outputs:
                self.last_tool_context = "\n".join(tool_outputs)

        if response:
            raw_content = response.content if hasattr(response, 'content') else str(response)
            
            if isinstance(raw_content, str):
                response_text = raw_content
            elif isinstance(raw_content, list):
                text_parts = []
                for block in raw_content:
                    if isinstance(block, str):
                        text_parts.append(block)
                    elif isinstance(block, dict) and 'text' in block:
                        text_parts.append(block['text'])
                    elif hasattr(block, 'text'):
                        text_parts.append(getattr(block, 'text', ''))
                response_text = " ".join(text_parts).strip()
            else:
                response_text = str(raw_content).strip()

            if not response_text or response_text in ["[]", "{}", "()"]:
                if self.last_tool_context:
                    response_text = f"Analyzed query. Context result:\n{self.last_tool_context}"
                else:
                    response_text = "I am ready for your command. What would you like to analyze?"

            try:
                print(f"[Agent Conscious Memory Response] {response_text}")
            except UnicodeEncodeError:
                print(f"[Agent Conscious Memory Response] {response_text.encode('ascii', 'ignore').decode('ascii')}")
            self._save_turn(user_query, response_text)
            return response_text

        # 4. Generic Fallback Response (No invented circuit details)
        fallback_msg = "No LLM backend is currently reachable. Please check your API keys or local Ollama server connection."
        self._save_turn(user_query, fallback_msg)
        return fallback_msg
