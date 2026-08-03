"""
Unit tests for tools/doc_exporter_tool.py (Jarvis PCB Copilot).
"""

import unittest
import os
from tools.doc_exporter_tool import export_engineering_doc

class TestDocExporterTool(unittest.TestCase):
    def test_export_engineering_doc(self):
        res = export_engineering_doc.invoke({
            "title": "Test Thermal Audit",
            "content": "Thermal power loss is 120mW.",
            "format_type": "markdown"
        })
        self.assertIn("Successfully exported engineering log", res)
        self.assertTrue(os.path.exists("docs/test_thermal_audit.md"))

if __name__ == "__main__":
    unittest.main()
