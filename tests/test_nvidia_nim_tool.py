"""
Unit tests for tools/nvidia_nim_tool.py (NVIDIA NIM Foundation Models integration).
"""

import os
import unittest
import base64
from unittest.mock import patch, MagicMock
from tools.nvidia_nim_tool import (
    NvidiaNIMClient,
    generate_nvidia_image,
    synthesize_nvidia_speech,
    transcribe_nvidia_audio
)


class TestNvidiaNIMTool(unittest.TestCase):
    def setUp(self):
        self.client = NvidiaNIMClient(api_key="nvapi-test-key-12345")

    def test_client_init_headers(self):
        headers = self.client._get_headers()
        self.assertEqual(headers["Authorization"], "Bearer nvapi-test-key-12345")

    @patch("tools.nvidia_nim_tool.requests.post")
    def test_generate_image(self, mock_post):
        # Mock base64 1x1 dummy image artifact response
        dummy_b64 = base64.b64encode(b"fake_image_data_bytes").decode("utf-8")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "artifacts": [{"base64": dummy_b64}]
        }
        mock_post.return_value = mock_response

        res = self.client.generate_image("a simple coffee shop interior", width=768, height=1344)
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["file_path"]))

    @patch("tools.nvidia_nim_tool.requests.post")
    def test_transcribe_audio(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "What is natural language processing?"}
        mock_post.return_value = mock_response

        # Create dummy audio file for testing
        test_wav = os.path.join("scratch", "test_sample.wav")
        os.makedirs("scratch", exist_ok=True)
        with open(test_wav, "wb") as f:
            f.write(b"RIFF dummy wav header")

        res_text = self.client.transcribe_audio(test_wav)
        self.assertEqual(res_text, "What is natural language processing?")

    @patch("tools.nvidia_nim_tool.requests.post")
    def test_synthesize_speech(self, mock_post):
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
        self.assertIn("Image generated successfully", tool_res)


if __name__ == "__main__":
    unittest.main()
