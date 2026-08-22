"""
🧪 Test Suite for Obsidian & Graphify Knowledge Graph Tool.
"""

import os
import sys
import unittest

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from tools.obsidian_knowledge_graph_tool import (
    generate_obsidian_knowledge_graph,
    query_knowledge_graph
)


class TestObsidianKnowledgeGraph(unittest.TestCase):

    def test_generate_and_query_obsidian_vault(self):
        print("\n--- Testing Obsidian Knowledge Graph Generation via Graphify ---")
        vault_out = os.path.abspath("obsidian_vault")
        res = generate_obsidian_knowledge_graph.invoke({
            "target_path": ".",
            "output_vault": "obsidian_vault",
            "code_only": True
        })

        self.assertEqual(res["status"], "success")
        data = res["data"]
        self.assertGreater(data["nodes_count"], 50)
        self.assertGreater(data["edges_count"], 50)
        self.assertGreater(data["notes_generated"], 0)
        self.assertTrue(os.path.exists(data["canvas_file"]))
        self.assertTrue(os.path.exists(data["html_visualization"]))

        print(f"Graph Metrics: {data['nodes_count']} nodes, {data['edges_count']} edges.")
        print(f"Generated Notes: {data['notes_generated']} Markdown files.")
        print(f"Canvas Path: {data['canvas_file']}")

        # Verify Query Tool
        print("\n--- Testing Knowledge Graph Query ---")
        q_res = query_knowledge_graph.invoke({"query_term": "copilot"})
        self.assertEqual(q_res["status"], "success")
        self.assertGreater(q_res["data"]["total_matches"], 0)
        print(f"Query Result Summary: {q_res['summary']}")
        print("✅ Obsidian & Graphify Knowledge Graph Test PASSED!")


if __name__ == "__main__":
    unittest.main()
