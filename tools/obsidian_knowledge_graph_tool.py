"""
🧠 Obsidian & Graphify Knowledge Graph Tool for Jarvis.

Integrates Graphify-Labs AST & Semantic Knowledge Graph Engine with Obsidian:
1. Extracts AST & Semantic relationships across codebases, schemas, and docs.
2. Exports a fully interconnected Obsidian Vault with [[wikilinks]], tags, and YAML frontmatter.
3. Generates Obsidian Infinite Canvas (.canvas) for visual whiteboard diagramming.
4. Generates an Agent Wiki with community clustering and architectural hub (god node) analysis.
5. Emits standalone interactive D3/WebGL graph views.
"""

import os
import sys
import json
import logging
import subprocess
from typing import Dict, Any, Optional, List
from langchain_core.tools import tool
import networkx as nx
from networkx.readwrite import json_graph
import config

logger = config.get_logger(__name__)


def _run_graphify_extract(target_dir: str, code_only: bool = True) -> str:
    """Executes graphify extraction subprocess."""
    venv_python = sys.executable
    cmd = [venv_python, "-m", "graphify.extract", target_dir]
    if code_only:
        cmd.append("--code-only")
    
    logger.info(f"[Graphify] Running extraction on '{target_dir}': {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=target_dir)
    if res.returncode != 0:
        logger.warning(f"[Graphify] Extraction notice: {res.stderr}")
    return res.stdout


def _build_obsidian_vault(
    graph_json_path: str,
    analysis_json_path: str,
    output_vault_dir: str
) -> Dict[str, Any]:
    """Generates Obsidian Vault, Canvas, and Wiki from graph.json."""
    from graphify.export import to_obsidian, to_canvas, to_html
    from graphify.wiki import to_wiki
    from graphify.cluster import label_communities_by_hub

    with open(graph_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    G = json_graph.node_link_graph(data, edges='links') if 'links' in data else json_graph.node_link_graph(data)

    analysis = {}
    if os.path.exists(analysis_json_path):
        with open(analysis_json_path, 'r', encoding='utf-8') as f:
            analysis = json.load(f)

    communities = {int(k): v for k, v in analysis.get('communities', {}).items()}
    labels = {int(k): v for k, v in analysis.get('community_labels', {}).items()}
    
    # Generate meaningful hub-based labels if none or default present
    if not labels or all(v.startswith("Community") for v in labels.values()):
        labels = label_communities_by_hub(G, communities)

    cohesion = {int(k): v for k, v in analysis.get('cohesion', {}).items()}

    os.makedirs(output_vault_dir, exist_ok=True)

    # 1. Export Obsidian Notes (.md with [[wikilinks]])
    notes_count = to_obsidian(G, communities, output_vault_dir, labels, cohesion)

    # 2. Export Obsidian Canvas (.canvas) with Hub Labels
    canvas_path = os.path.join(output_vault_dir, "Architecture_Graph.canvas")
    to_canvas(G, communities, canvas_path, labels)

    # 3. Export Agent Wiki
    wiki_dir = os.path.join(output_vault_dir, "Wiki")
    wiki_count = to_wiki(G, communities, wiki_dir, labels, cohesion)

    # 4. Export Interactive HTML Graph
    html_path = os.path.join(output_vault_dir, "Interactive_Graph.html")
    to_html(G, communities, html_path, labels)

    # 5. Create fine-tuned .obsidian graph settings
    obsidian_config_dir = os.path.join(output_vault_dir, ".obsidian")
    os.makedirs(obsidian_config_dir, exist_ok=True)
    graph_config = {
        "collapse-filter": False,
        "search": "",
        "tags": True,
        "showLinks": True,
        "showArrow": True,
        "textFadeMultiplier": -0.2,
        "nodeSizeMultiplier": 1.35,
        "lineSizeMultiplier": 1.4,
        "colorGroups": [
            {"query": "path:agent/security OR path:agent/code_pipeline OR path:agent/task_runner", "color": {"a": 1, "rgb": 9133302}}, # Purple (Autonomous Execution & Security)
            {"query": "path:tools/kicad OR file:KiCad", "color": {"a": 1, "rgb": 3978495}},       # Emerald Green
            {"query": "path:agent OR file:copilot", "color": {"a": 1, "rgb": 54271}},             # Cyber Blue
            {"query": "path:gateway OR file:gateway", "color": {"a": 1, "rgb": 65535}},           # Neon Cyan
            {"query": "path:composio OR file:composio", "color": {"a": 1, "rgb": 16744272}},      # Amber Gold
            {"query": "file:thermal OR file:autoroute", "color": {"a": 1, "rgb": 16731983}},      # Bright Orange
            {"query": "file:manufacturing OR file:export", "color": {"a": 1, "rgb": 11342935}}   # Violet
        ]
    }
    with open(os.path.join(obsidian_config_dir, "graph.json"), "w", encoding="utf-8") as f:
        json.dump(graph_config, f, indent=2)

    # 6. Generate Architectural Hub Notes
    _generate_subsystem_hub_notes(output_vault_dir)

    return {
        "nodes_count": G.number_of_nodes(),
        "edges_count": G.number_of_edges(),
        "communities_count": len(communities),
        "notes_generated": notes_count,
        "wiki_articles": wiki_count,
        "canvas_file": canvas_path,
        "html_visualization": html_path,
        "vault_path": output_vault_dir
    }


def _generate_subsystem_hub_notes(vault_dir: str):
    """Generates first-class subsystem hub notes in the Obsidian Vault."""
    wiki_dir = os.path.join(vault_dir, "Wiki")
    os.makedirs(wiki_dir, exist_ok=True)

    hubs = {
        "Hub_Autonomous_Coding.md": (
            "# 🛠️ Hub: Autonomous Code Pipeline\n\n"
            "**Purpose:** End-to-end software code generation, AST syntax verification, and sandboxed test execution.\n\n"
            "## Key Modules & Typed Relationships\n"
            "- [[code_pipeline]] --generates--> [[write_and_verify_code]]\n"
            "- [[write_and_verify_code]] --verified-by--> [[AgenticCodeVerifyLoop]]\n"
            "- [[code_pipeline]] --gates--> [[AgentShieldGuard]]\n"
            "- [[TaskRunner]] --plans--> [[code_pipeline]]\n"
        ),
        "Hub_Security.md": (
            "# 🛡️ Hub: AgentShield Security v2\n\n"
            "**Purpose:** Hardened path jail, Job Object sandboxing, secret scrubbing, and prompt-injection filtering.\n\n"
            "## Key Modules & Typed Relationships\n"
            "- [[security]] --gates--> [[TaskRunner]]\n"
            "- [[security]] --gates--> [[code_pipeline]]\n"
            "- [[security]] --reports-to--> [[audit_log]]\n"
            "- [[ApprovalGate]] --blocks--> [[TaskNode]]\n"
        ),
        "Hub_Task_Runner.md": (
            "# 📊 Hub: Universal DAG TaskRunner\n\n"
            "**Purpose:** Asynchronous DAG scheduler, durable SQLite task persistence, and crash recovery.\n\n"
            "## Key Modules & Typed Relationships\n"
            "- [[task_runner]] --depends-on--> [[DurableTaskStore]]\n"
            "- [[task_runner]] --reports-to--> [[GoalsKanban]]\n"
            "- [[task_runner]] --mirrors--> [[Runs]]\n"
            "- [[LocalOrchestrator]] --plans--> [[TaskRunner]]\n"
        ),
        "Hub_Search_Routing.md": (
            "# 🌐 Hub: Explicit Search & Web Gateway\n\n"
            "**Purpose:** High-accuracy web search routing with source citations and 4-tier anti-bot escalation.\n\n"
            "## Key Modules & Typed Relationships\n"
            "- [[reach_tool]] --routes-through--> [[search_web_explicit]]\n"
            "- [[search_web_explicit]] --escalates-via--> [[EscalationEngine]]\n"
            "- [[LocalOrchestrator]] --routes-through--> [[reach_tool]]\n"
        ),
        "Edge_Taxonomy.md": (
            "# 🏷️ Typed Edge Taxonomy for Jarvis Knowledge Graph\n\n"
            "This taxonomy defines the formal set of typed relationship verbs used in the Jarvis Obsidian Knowledge Graph.\n\n"
            "| Verb | Semantics | Example Source -> Target |\n"
            "| :--- | :--- | :--- |\n"
            "| **`plans`** | Upstream orchestrator breaks down a prompt into DAG steps. | `LocalOrchestrator` --plans--> `TaskRunner` |\n"
            "| **`generates`** | Component generates code, artifacts, or responses. | `code_pipeline` --generates--> `write_and_verify_code` |\n"
            "| **`verifies`** | Verification loop executes tests/AST checks on code. | `AgenticCodeVerifyLoop` --verifies--> `code_pipeline` |\n"
            "| **`gates`** | Security layer enforces checks before execution. | `AgentShieldGuard` --gates--> `TaskRunner` |\n"
            "| **`routes-through`** | Intent triage routes user queries to specific tools. | `LocalOrchestrator` --routes-through--> `reach_tool` |\n"
            "| **`depends-on`** | DAG node requires completion of a parent node. | `TaskNode_step2` --depends-on--> `TaskNode_step1` |\n"
            "| **`blocks`** | Human approval gate pauses DAG execution pending token. | `ApprovalGate` --blocks--> `TaskNode` |\n"
            "| **`reports-to`** | Execution engine synchronizes status with telemetry/Kanban. | `TaskRunner` --reports-to--> `GoalsKanban` |\n"
            "| **`mirrors`** | Task execution record is mirrored to Obsidian vault. | `TaskRunner` --mirrors--> `Runs/` |\n"
        )
    }

    for filename, content in hubs.items():
        hub_path = os.path.join(wiki_dir, filename)
        with open(hub_path, "w", encoding="utf-8") as f:
            f.write(content)


def mirror_task_run_to_vault(task_id: str, prompt: str, steps_data: List[Dict[str, Any]], vault_dir: str = "obsidian_vault"):
    """Mirrors a completed TaskRunner execution to obsidian_vault/Runs/."""
    runs_dir = os.path.join(vault_dir, "Runs")
    os.makedirs(runs_dir, exist_ok=True)
    date_str = time.strftime("%Y-%m-%d")
    run_file = os.path.join(runs_dir, f"{date_str}_{task_id}.md")
    
    lines = [
        f"# 🏃 Task Run: {task_id}\n",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Prompt:** {prompt}\n",
        f"## Executed Steps & Typed Traceability",
    ]
    for s in steps_data:
        s_name = s.get("name", "Step")
        s_role = s.get("role", "executor")
        lines.append(f"- [[{task_id}]] --executed--> [[{s_name}]] (`{s_role}`)")
    
    with open(run_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


@tool
def generate_obsidian_knowledge_graph(
    target_path: str = ".",
    output_vault: str = "obsidian_vault",
    code_only: bool = True
) -> dict:
    """
    Analyzes any codebase or documents using Graphify and generates a full Obsidian Knowledge Graph Vault.
    Produces interconnected [[wikilink]] Markdown notes, Obsidian Canvas visual whiteboards, an Agent Wiki, and interactive graph views.

    Args:
        target_path: Path to codebase, documentation folder, or project directory to analyze (default: current workspace).
        output_vault: Path to output Obsidian Vault folder (default: 'obsidian_vault').
        code_only: If True, uses local deterministic AST parsing without external API cost.

    Returns:
        dict containing node count, edge count, generated notes, canvas file location, and vault directory.
    """
    abs_target = os.path.abspath(target_path)
    abs_output = os.path.abspath(output_vault)

    logger.info(f"[Obsidian Tool] Generating knowledge graph for '{abs_target}' into '{abs_output}'")

    # Step 1: Run Graphify Extraction
    _run_graphify_extract(abs_target, code_only=code_only)

    graph_json = os.path.join(abs_target, "graphify-out", "graph.json")
    analysis_json = os.path.join(abs_target, "graphify-out", ".graphify_analysis.json")

    if not os.path.exists(graph_json):
        return {
            "status": "error",
            "summary": f"Graphify extraction failed: '{graph_json}' not created.",
            "data": None
        }

    # Step 2: Build Obsidian Vault & Canvas
    result = _build_obsidian_vault(graph_json, analysis_json, abs_output)

    summary = (
        f"Obsidian Knowledge Graph generated successfully in '{abs_output}'!\n"
        f"Graph Metrics: {result['nodes_count']} nodes, {result['edges_count']} edges across {result['communities_count']} community clusters.\n"
        f"Generated {result['notes_generated']} backlinked Markdown notes, Obsidian Canvas '{os.path.basename(result['canvas_file'])}', and Agent Wiki ({result['wiki_articles']} articles)."
    )

    return {
        "status": "success",
        "summary": summary,
        "data": result
    }


@tool
def query_knowledge_graph(
    query_term: str,
    graph_json_path: str = "graphify-out/graph.json"
) -> dict:
    """
    Queries the extracted Knowledge Graph for architectural hubs (god nodes), dependencies, and connected symbols.

    Args:
        query_term: Symbol, function, class, or module name to inspect.
        graph_json_path: Path to graph.json.

    Returns:
        dict with connected neighbors, inbound/outbound dependencies, and degree centrality.
    """
    if not os.path.exists(graph_json_path):
        return {"status": "error", "summary": f"Graph file '{graph_json_path}' not found. Run generate_obsidian_knowledge_graph first."}

    with open(graph_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    G = json_graph.node_link_graph(data, edges='links') if 'links' in data else json_graph.node_link_graph(data)

    matches = [n for n in G.nodes if query_term.lower() in str(n).lower()]
    if not matches:
        return {"status": "success", "summary": f"No nodes matched query '{query_term}'.", "data": {"matches": []}}

    results = []
    for node in matches[:10]:
        in_edges = list(G.predecessors(node)) if G.is_directed() else list(G.neighbors(node))
        out_edges = list(G.successors(node)) if G.is_directed() else list(G.neighbors(node))
        node_attr = G.nodes[node]
        results.append({
            "node": node,
            "type": node_attr.get("type", "unknown"),
            "file": node_attr.get("file", ""),
            "degree": G.degree(node),
            "inbound_callers": in_edges[:10],
            "outbound_dependencies": out_edges[:10]
        })

    summary = f"Found {len(matches)} matching node(s) for '{query_term}' in knowledge graph."
    return {
        "status": "success",
        "summary": summary,
        "data": {"query": query_term, "total_matches": len(matches), "nodes": results}
    }
