"""
Unit tests for tools/unlimited_ocr_tool.py (Baidu Unlimited-OCR integration).
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from tools.unlimited_ocr_tool import UnlimitedOCRTool, parse_document_unlimited_ocr


class TestUnlimitedOCRTool(unittest.TestCase):
    def setUp(self):
        self.ocr_tool = UnlimitedOCRTool()
        self.test_pdf = os.path.join("scratch", "test_doc.pdf")
        os.makedirs("scratch", exist_ok=True)
        with open(self.test_pdf, "wb") as f:
            f.write(b"%PDF-1.4 dummy pdf content for testing")

    def test_init(self):
        self.assertEqual(self.ocr_tool.model_name, "baidu/Unlimited-OCR")

    @patch("tools.unlimited_ocr_tool.glob.glob", return_value=[])
    def test_parse_missing_file(self, mock_glob):
        res = self.ocr_tool.parse_document("non_existent_file_9999.pdf")
        self.assertIn("Unlimited-OCR Error", res)

    @patch("tools.nvidia_nim_tool.NvidiaNIMClient.invoke_nemotron_ocr", return_value="### Extracted table data")
    @patch("tools.unlimited_ocr_tool.UnlimitedOCRTool.load_model_if_needed", return_value=False)
    def test_parse_sample_pdf(self, mock_load, mock_ocr):
        res = self.ocr_tool.parse_document(self.test_pdf)
        self.assertIn("Unlimited-OCR Document Analysis", res)
        self.assertTrue(os.path.exists(os.path.join("scratch", "unlimited_ocr_test_doc.md")))

    @patch("tools.nvidia_nim_tool.NvidiaNIMClient.invoke_nemotron_ocr", return_value="### Extracted table data")
    @patch("tools.unlimited_ocr_tool.UnlimitedOCRTool.load_model_if_needed", return_value=False)
    def test_langchain_tool(self, mock_load, mock_ocr):
        tool_res = parse_document_unlimited_ocr.invoke({"document_path": self.test_pdf})
        self.assertIn("Unlimited-OCR Document Analysis", tool_res)


if __name__ == "__main__":
    unittest.main()
