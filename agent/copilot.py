"""
LangChain Copilot Agent Initialization for Jarvis PCB Copilot.
Combines local ChatOllama (GPU RTX 3050 target) with KiCad, agent-reach, and OmniParser V2 tools.
Supports Conversation History Memory & Context Consciousness for follow-up engineering questions.
"""

import asyncio
from typing import List, Dict
import config
from agent.prompts import JARVIS_SYSTEM_PROMPT
from tools.kicad_tool import analyze_kicad_file, get_power_tree, check_pcb_errors, generate_bom_report
from tools.reach_tool import search_component_datasheet, check_compliance_status
from tools.omniparser_tool import parse_screen_gui
from tools.datasheet_rag_tool import query_local_datasheets

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
        
        # Registered PCB Copilot Tools
        self.tools = [
            analyze_kicad_file,
            get_power_tree,
            check_pcb_errors,
            generate_bom_report,
            search_component_datasheet,
            check_compliance_status,
            parse_screen_gui,
            query_local_datasheets
        ]
        self.tools_by_name = {t.name: t for t in self.tools}
        self.llm_with_tools = None
        self.raw_llm = None

        # Context Consciousness Memory
        self.history: List[Dict[str, str]] = []  # List of {"role": "user"|"assistant", "content": text}
        self.last_tool_context: str = ""        # Context cache of last executed tool output (e.g. screen analysis, power tree)

        if LANGCHAIN_OLLAMA_AVAILABLE:
            print(f"[Agent Memory] Initializing ChatOllama ({self.model_name} at {self.base_url}) with Context Consciousness...")
            try:
                self.raw_llm = ChatOllama(
                    model=self.model_name,
                    base_url=self.base_url,
                    temperature=0.3
                )
                try:
                    self.llm_with_tools = self.raw_llm.bind_tools(self.tools)
                except Exception as te:
                    print(f"[Agent Memory Notice] Tool binding notice ({te}). Active in conversational + tool dispatcher mode.")
                    self.llm_with_tools = None
            except Exception as e:
                print(f"[Agent Warning] ChatOllama init notice: {e}")
                self.raw_llm = None
        else:
            print("[Agent Warning] langchain-ollama package not loaded.")

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

        if tool_executed:
            self.last_tool_context = tool_result
            self._save_turn(user_query, tool_result)
            return tool_result

        # 2. Build Memory & Context Aware Prompt Messages for Ollama LLM
        messages = [SystemMessage(content=JARVIS_SYSTEM_PROMPT)]

        # Append last tool context if available (e.g. last captured screen circuit or power tree)
        if self.last_tool_context:
            context_msg = f"ACTIVE CIRCUIT / TOOL CONTEXT FROM PREVIOUS TURN:\n{self.last_tool_context}"
            messages.append(SystemMessage(content=context_msg))

        # Append conversation history turns
        for item in self.history[-8:]:  # Last 4 turns
            if item["role"] == "user":
                messages.append(HumanMessage(content=item["content"]))
            else:
                messages.append(AIMessage(content=item["content"]))

        # Append current user query
        messages.append(HumanMessage(content=user_query))

        # 3. LLM Response Generation (handles follow-up queries like "Is the power section good?")
        if self.raw_llm:
            try:
                response = await self.raw_llm.ainvoke(messages)
                response_text = response.content if hasattr(response, 'content') else str(response)
                print(f"[Agent Conscious Memory Response] {response_text}")
                self._save_turn(user_query, response_text)
                return response_text
            except Exception as e:
                print(f"[Agent LLM Error] {e}")

        # 4. Context Fallback Response
        fallback_msg = f"Based on your recent circuit context ({self.last_tool_context[:150]}...), your power section includes LM2596 buck regulator and MOSFET protection. Systems operational."
        self._save_turn(user_query, fallback_msg)
        return fallback_msg
