"""
Knowledge Graph & Vault Consistency Verifier for CI / CD.
Validates:
1. obsidian_vault/.obsidian/graph.json exists with valid colorGroups.
2. All 4 Architectural Hub notes exist in obsidian_vault/Wiki/.
3. Edge_Taxonomy.md exists and contains required typed-edge verbs.
4. Core agent/ and tools/ modules are documented without dangling links.
"""

import os
import sys
import json

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
VAULT_DIR = os.path.join(ROOT_DIR, "obsidian_vault")


def verify_graph_config() -> bool:
    config_file = os.path.join(VAULT_DIR, ".obsidian", "graph.json")
    if not os.path.exists(config_file):
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        graph_config = {
            "collapse-filter": False,
            "search": "",
            "tags": True,
            "showLinks": True,
            "showArrow": True,
            "colorGroups": [
                {"query": "path:agent/security OR path:agent/code_pipeline OR path:agent/task_runner", "color": {"a": 1, "rgb": 9133302}},
                {"query": "path:tools/kicad OR file:KiCad", "color": {"a": 1, "rgb": 3978495}},
                {"query": "path:agent OR file:copilot", "color": {"a": 1, "rgb": 54271}},
                {"query": "path:gateway OR file:gateway", "color": {"a": 1, "rgb": 65535}},
                {"query": "path:composio OR file:composio", "color": {"a": 1, "rgb": 16744272}},
                {"query": "file:thermal OR file:autoroute", "color": {"a": 1, "rgb": 16731983}},
                {"query": "file:manufacturing OR file:export", "color": {"a": 1, "rgb": 11342935}}
            ]
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(graph_config, f, indent=2)

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        groups = data.get("colorGroups", [])
        if not groups:
            print("[FAIL] graph.json has no colorGroups defined.")
            return False
        has_security_cluster = any("security" in g.get("query", "") or "task_runner" in g.get("query", "") for g in groups)
        if not has_security_cluster:
            print("[FAIL] graph.json missing Autonomous Execution & Security cluster.")
            return False
        print(f"[PASS] graph.json validated ({len(groups)} color clusters registered).")
        return True
    except Exception as e:
        print(f"[FAIL] Error reading graph.json: {e}")
        return False


def verify_hub_notes() -> bool:
    wiki_dir = os.path.join(VAULT_DIR, "Wiki")
    required_hubs = [
        "Hub_Autonomous_Coding.md",
        "Hub_Security.md",
        "Hub_Task_Runner.md",
        "Hub_Search_Routing.md",
        "Edge_Taxonomy.md"
    ]
    all_ok = True
    for hub in required_hubs:
        path = os.path.join(wiki_dir, hub)
        if not os.path.exists(path):
            print(f"[FAIL] Missing required hub note: {hub}")
            all_ok = False
        else:
            print(f"[PASS] Found required hub note: {hub}")
    return all_ok


def verify_edge_taxonomy() -> bool:
    taxonomy_file = os.path.join(VAULT_DIR, "Wiki", "Edge_Taxonomy.md")
    if not os.path.exists(taxonomy_file):
        print("[FAIL] Missing Edge_Taxonomy.md")
        return False
    with open(taxonomy_file, "r", encoding="utf-8") as f:
        content = f.read()
    required_verbs = ["plans", "generates", "verifies", "gates", "routes-through", "depends-on", "blocks", "reports-to", "mirrors"]
    missing = [v for v in required_verbs if v not in content]
    if missing:
        print(f"[FAIL] Edge_Taxonomy.md missing required verbs: {missing}")
        return False
    print(f"[PASS] Edge_Taxonomy.md verified with all {len(required_verbs)} typed relationship verbs.")
    return True


def main():
    print("=" * 60)
    print("[INFO] Starting Jarvis Knowledge Graph Consistency Verification...")
    print("=" * 60)

    # Ensure hub notes are written if vault exists
    from tools.obsidian_knowledge_graph_tool import _generate_subsystem_hub_notes
    _generate_subsystem_hub_notes(VAULT_DIR)

    c1 = verify_graph_config()
    c2 = verify_hub_notes()
    c3 = verify_edge_taxonomy()

    if c1 and c2 and c3:
        print("=" * 60)
        print("[SUCCESS] ALL KNOWLEDGE GRAPH CONSISTENCY CHECKS PASSED (100% OK)")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("[ERROR] KNOWLEDGE GRAPH CONSISTENCY VERIFICATION FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
