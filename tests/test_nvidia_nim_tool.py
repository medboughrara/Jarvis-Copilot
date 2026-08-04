"""
Unit & Integration Tests for tools/nvidia_nim_tool.py (NVIDIA NIM Cloud Foundation Models).
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from tools.nvidia_nim_tool import NvidiaNIMClient, generate_nvidia_image, synthesize_nvidia_speech, run_nvidia_reasoning


class TestNvidiaNIMTool(unittest.TestCase):
    def setUp(self):
        self.client = NvidiaNIMClient(api_key="test-nvapi-key")

    @patch("requests.post")
    def test_generate_image_mock(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "artifacts": [{"base64": "aGVsbG8="}]
        }
        mock_post.return_value = mock_response

        res = self.client.generate_image("a simple coffee shop interior")
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["file_path"]))

    @patch("requests.post")
    def test_synthesize_speech_mock(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "audio/wav"}
        mock_response.content = b"RIFF dummy wav audio data"
        mock_post.return_value = mock_response

        res = self.client.synthesize_speech("Hello from NVIDIA Magpie TTS")
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["file_path"]))

    @patch("tools.nvidia_nim_tool.NvidiaNIMClient.generate_image")
    def test_langchain_generate_nvidia_image_tool(self, mock_gen):
        mock_gen.return_value = {
            "status": "success",
            "file_path": "scratch/nvidia_flux_test.png"
        }
        tool_res = generate_nvidia_image.invoke({"prompt": "a simple coffee shop interior"})
        self.assertEqual(tool_res["status"], "success")
        self.assertIn("file_path", tool_res["data"])


if __name__ == "__main__":
    unittest.main()
