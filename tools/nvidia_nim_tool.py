"""
NVIDIA NIM Foundation Models Integration Tool for Jarvis PCB Copilot.
Integrates NVIDIA Cloud Foundation Models:
1. FLUX.1-Schnell (black-forest-labs/flux.1-schnell) - Text-to-Image Generation
2. Whisper-Large-v3 (openai/whisper-large-v3) - Cloud Speech-to-Text
3. Magpie-TTS-Multilingual (nvidia/magpie-tts-multilingual) - Multilingual Text-to-Speech
4. Moonshot AI Kimi 2.6 (moonshotai/kimi-k2.6) - Deep Reasoning & LLM Analysis
5. NVIDIA Nemotron 3 Nano Omni 30B (nvidia/nemotron-3-nano-omni-30b-a3b-reasoning) - Multimodal Hardware Reasoning
6. NVIDIA Nemotron OCR v2 (nvidia/nemotron-ocr-v2) - Visual Document & Schematic OCR
7. NVIDIA Nemotron 3 Embed 1B (nvidia/nemotron-3-embed-1b) - High-Speed Datasheet RAG Embeddings
"""

import os
import time
import base64
import json
import requests
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)


class NvidiaNIMClient:
    """Client wrapper for NVIDIA AI Foundation Models (NIM Cloud APIs)."""

    def __init__(self, api_key: str = None):
        self.api_key = (api_key or config.NVIDIA_API_KEY or "").strip()
        self.flux_url = config.NVIDIA_FLUX_URL
        self.whisper_url = config.NVIDIA_WHISPER_URL
        self.magpie_url = config.NVIDIA_MAGPIE_URL
        self.integrate_chat_url = config.NVIDIA_INTEGRATE_CHAT_URL
        self.nemotron_ocr_url = config.NVIDIA_NEMOTRON_OCR_URL
        self.embed_url = config.NVIDIA_EMBED_URL

    def _get_headers(self, accept: str = "application/json", key: str = None) -> dict:
        use_key = key or self.api_key
        if not use_key:
            raise ValueError(
                "NVIDIA API Key not configured. Please set NVIDIA_API_KEY in your .env file or environment."
            )
        return {
            "Authorization": f"Bearer {use_key}",
            "Accept": accept,
        }

    def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        seed: int = 1,
        steps: int = 4
    ) -> dict:
        """
        Generates images using NVIDIA FLUX.1-Schnell API and saves to scratch/ directory.
        """
        if not self.api_key:
            return {
                "status": "error",
                "message": "NVIDIA API Key missing. Set NVIDIA_API_KEY in .env file."
            }

        logger.info(f"[NVIDIA FLUX.1-Schnell] Generating image for prompt: '{prompt}' ({width}x{height})...")
        headers = self._get_headers(accept="application/json")
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "seed": seed,
            "steps": steps
        }

        try:
            response = requests.post(self.flux_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            res_body = response.json()

            os.makedirs("scratch", exist_ok=True)
            timestamp = int(time.time())
            output_file = os.path.join("scratch", f"nvidia_flux_{timestamp}.png")

            artifacts = res_body.get("artifacts", [])
            b64_data = None

            if artifacts and isinstance(artifacts, list):
                b64_data = artifacts[0].get("base64") or artifacts[0].get("b64_json")
            elif "b64_json" in res_body:
                b64_data = res_body["b64_json"]
            elif "image" in res_body:
                b64_data = res_body["image"]

            if b64_data:
                image_bytes = base64.b64decode(b64_data)
                with open(output_file, "wb") as f:
                    f.write(image_bytes)
                logger.info(f"[NVIDIA FLUX.1-Schnell] Image saved to {output_file}")
                return {
                    "status": "success",
                    "file_path": output_file,
                    "prompt": prompt,
                    "raw_response": res_body
                }

            return {
                "status": "success",
                "file_path": output_file,
                "prompt": prompt,
                "raw_response": res_body
            }

        except Exception as e:
            logger.error(f"[NVIDIA FLUX.1-Schnell Error] {e}")
            return {
                "status": "error",
                "message": f"NVIDIA FLUX.1-Schnell API error: {e}"
            }

    def transcribe_audio(self, audio_file: str) -> str:
        """
        Transcribes spoken audio using NVIDIA Whisper Large v3 Cloud API.
        """
        if not self.api_key:
            return "[Error: NVIDIA_API_KEY not configured. Set NVIDIA_API_KEY in .env file.]"

        if not os.path.exists(audio_file):
            return f"[Error: Audio file '{audio_file}' not found.]"

        logger.info(f"[NVIDIA Whisper Large v3] Transcribing '{audio_file}'...")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }

        try:
            with open(audio_file, "rb") as f:
                files = {"file": f}
                data = {"model": "openai/whisper-large-v3", "language": "en"}
                response = requests.post(self.whisper_url, headers=headers, files=files, data=data, timeout=30)
                
            response.raise_for_status()
            res_json = response.json()
            text = res_json.get("text", "") or res_json.get("transcription", "")
            return text.strip() if text else str(res_json)
        except Exception as e:
            logger.error(f"[NVIDIA Whisper v3 Error] {e}")
            return f"[Error in NVIDIA Whisper v3 transcription: {e}]"

    def synthesize_speech(self, text: str, language: str = "English (US)", voice: str = "English (US)") -> dict:
        """
        Synthesizes spoken audio using NVIDIA Magpie Multilingual TTS API.
        """
        if not self.api_key:
            return {
                "status": "error",
                "message": "NVIDIA API Key missing. Set NVIDIA_API_KEY in .env file."
            }

        logger.info(f"[NVIDIA Magpie TTS] Synthesizing speech for: '{text[:40]}...'")
        headers = self._get_headers(accept="audio/wav")
        headers["Content-Type"] = "application/json"
        
        payload = {
            "text": text,
            "language": language,
            "voice": voice
        }

        try:
            response = requests.post(self.magpie_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            os.makedirs("scratch", exist_ok=True)
            timestamp = int(time.time())
            output_file = os.path.join("scratch", f"nvidia_magpie_{timestamp}.wav")

            if "audio" in response.headers.get("Content-Type", "") or response.content[:4] == b"RIFF":
                with open(output_file, "wb") as f:
                    f.write(response.content)
            else:
                try:
                    res_json = response.json()
                    b64_audio = res_json.get("audio") or res_json.get("audio_content")
                    if b64_audio:
                        with open(output_file, "wb") as f:
                            f.write(base64.b64decode(b64_audio))
                except Exception:
                    with open(output_file, "wb") as f:
                        f.write(response.content)

            return {
                "status": "success",
                "file_path": output_file,
                "text": text
            }
        except Exception as e:
            logger.error(f"[NVIDIA Magpie TTS Error] {e}")
            return {
                "status": "error",
                "message": f"NVIDIA Magpie TTS error: {e}"
            }

    def invoke_chat_completion(
        self,
        messages: list,
        model: str = "moonshotai/kimi-k2.6",
        api_key: str = None,
        max_tokens: int = 16384,
        reasoning_budget: int = None
    ) -> str:
        """
        Invokes NVIDIA Chat Completion API for Kimi 2.6 or Nemotron 3 Reasoning models.
        """
        use_key = api_key or (config.NVIDIA_KIMI_KEY if "kimi" in model else config.NVIDIA_NEMOTRON_KEY) or self.api_key
        if not use_key:
            return f"[Error: No API key configured for model '{model}'.]"

        headers = {
            "Authorization": f"Bearer {use_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        msg_payload = messages if isinstance(messages, list) else [{"role": "user", "content": str(messages)}]

        payload = {
            "messages": msg_payload,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 0.6 if "nemotron" in model else 1,
            "top_p": 0.95 if "nemotron" in model else 1,
            "stream": False
        }
        if reasoning_budget and "nemotron" in model:
            payload["reasoning_budget"] = reasoning_budget

        try:
            res = requests.post(self.integrate_chat_url, headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            res_data = res.json()
            choices = res_data.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "")
            return str(res_data)
        except Exception as e:
            logger.error(f"[NVIDIA Chat API Error - {model}] {e}")
            return f"[Error calling NVIDIA Chat API ({model}): {e}]"

    def invoke_nemotron_ocr(self, image_file: str = "") -> str:
        """
        Uses NVIDIA Nemotron OCR v2 for robust text & component recognition on schematic screenshots or datasheets.
        """
        key = config.NVIDIA_NEMOTRON_OCR_KEY or self.api_key
        if not key:
            return "[Error: NVIDIA_NEMOTRON_OCR_KEY missing.]"

        if not image_file:
            image_file = os.path.join("scratch", "screen_capture.png")

        if not os.path.exists(image_file):
            return f"[Error: Image file '{image_file}' not found for Nemotron OCR.]"

        logger.info(f"[NVIDIA Nemotron OCR v2] Processing '{image_file}'...")
        headers = {
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            with open(image_file, "rb") as img_f:
                b64_img = base64.b64encode(img_f.read()).decode("utf-8")

            payload = {
                "model": "nvidia/nemotron-ocr-v2",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all text, schematic components, pin references, and values from this PCB visual layout."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                        ]
                    }
                ]
            }
            res = requests.post(self.integrate_chat_url, headers=headers, json=payload, timeout=60)
            if res.status_code == 200:
                res_data = res.json()
                choices = res_data.get("choices", [])
                if choices:
                    return choices[0]["message"].get("content", "")
            return f"Nemotron OCR completed with response code: {res.status_code}"
        except Exception as e:
            logger.error(f"[NVIDIA Nemotron OCR Error] {e}")
            return f"[Error in Nemotron OCR v2: {e}]"

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Gets embedding vectors using NVIDIA Nemotron 3 Embed 1B (nemotron-3-embed-1b).
        """
        key = config.NVIDIA_NEMOTRON_EMBED_KEY or self.api_key
        if not key:
            raise ValueError("NVIDIA_NEMOTRON_EMBED_KEY missing.")

        headers = {
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "input": texts,
            "model": "nvidia/nemotron-3-embed-1b",
            "input_type": "query",
            "encoding_format": "float"
        }
        res = requests.post(self.embed_url, headers=headers, json=payload, timeout=30)
        res.raise_for_status()
        data = res.json()
        embeddings = [item["embedding"] for item in data.get("data", [])]
        return embeddings


# ---------------------------------------------------------------------------
# LangChain Tool Exports
# ---------------------------------------------------------------------------

@tool
def generate_nvidia_image(prompt: str, width: int = 1024, height: int = 1024) -> str:
    """
    Generates high-resolution PCB block diagrams, lab interiors, or concept artwork using NVIDIA FLUX.1-Schnell.
    Args:
        prompt: Descriptive prompt for image generation (e.g. 'a simple coffee shop interior', 'KiCad PCB schematic block diagram').
        width: Image width in pixels (default: 1024).
        height: Image height in pixels (default: 1024).
    """
    client = NvidiaNIMClient()
    res = client.generate_image(prompt=prompt, width=width, height=height)
    if res["status"] == "success":
        return f"NVIDIA FLUX.1-Schnell Image generated successfully! Saved to: {res['file_path']}"
    return f"Image generation failed: {res.get('message', 'Unknown error')}"


@tool
def synthesize_nvidia_speech(text: str, language: str = "English (US)") -> str:
    """
    Synthesizes natural, human-like voice audio using NVIDIA Magpie Multilingual TTS.
    Args:
        text: Speech text to synthesize into spoken voice audio.
        language: Target language (default: 'English (US)').
    """
    client = NvidiaNIMClient()
    res = client.synthesize_speech(text=text, language=language)
    if res["status"] == "success":
        return f"NVIDIA Magpie TTS synthesized voice audio successfully! Saved to: {res['file_path']}"
    return f"NVIDIA Magpie TTS failed: {res.get('message', 'Unknown error')}"


@tool
def transcribe_nvidia_audio(audio_file: str) -> str:
    """
    Transcribes audio commands using NVIDIA Whisper Large v3 Cloud API.
    Args:
        audio_file: Path to audio file (.wav) to transcribe.
    """
    client = NvidiaNIMClient()
    return client.transcribe_audio(audio_file)


@tool
def run_nvidia_reasoning(query: str, model_choice: str = "kimi-k2.6") -> str:
    """
    Executes deep hardware reasoning and architectural analysis using Moonshot Kimi 2.6 or NVIDIA Nemotron 3 Reasoning models.
    Args:
        query: Engineering question or architectural review request.
        model_choice: 'kimi-k2.6' or 'nemotron-3-nano-omni-30b-a3b-reasoning'.
    """
    client = NvidiaNIMClient()
    model = "moonshotai/kimi-k2.6" if "kimi" in model_choice.lower() else "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    budget = 16384 if "nemotron" in model else None
    return client.invoke_chat_completion(messages=[{"role": "user", "content": query}], model=model, reasoning_budget=budget)


@tool
def parse_nemotron_ocr(image_path: str = "") -> str:
    """
    Extracts text, table values, component designations, and pinouts from PCB screenshots or PDF datasheets using NVIDIA Nemotron OCR v2.
    Args:
        image_path: Optional path to screenshot or schematic image file.
    """
    client = NvidiaNIMClient()
    return client.invoke_nemotron_ocr(image_path)
