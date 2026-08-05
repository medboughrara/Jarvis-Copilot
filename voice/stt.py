"""
Speech-to-Text module using Faster-Whisper (CPU INT8 quantized).
Transcribes user spoken commands with domain-specific bias prompts.
"""

import os
import asyncio
import numpy as np
from faster_whisper import WhisperModel
import config

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except OSError as e:
    print(f"[STT Audio Error] sounddevice import failed: {e}")
    AUDIO_AVAILABLE = False


class Transcriber:
    def __init__(self):
        print(f"[STT] Loading Faster-Whisper ({config.STT_MODEL_SIZE}) on {config.STT_DEVICE} with {config.STT_COMPUTE_TYPE}...")
        self.model = WhisperModel(
            config.STT_MODEL_SIZE,
            device=config.STT_DEVICE,
            compute_type=config.STT_COMPUTE_TYPE
        )
        self.initial_prompt = config.STT_INITIAL_PROMPT
        print(f"[STT] Transcriber ready with prompt: '{self.initial_prompt}'")

    async def record_user_audio(self, record_seconds: float = 5.0) -> np.ndarray:
        """
        Records microphone input for a specified duration after wake word activation.
        """
        if not AUDIO_AVAILABLE:
            print("[STT] Audio device unavailable. Simulating silence...")
            await asyncio.sleep(1)
            # Return empty audio array
            return np.zeros(int(record_seconds * config.SAMPLE_RATE), dtype=np.float32)

        loop = asyncio.get_running_loop()
        print(f"[STT] Listening for user command ({record_seconds}s)... Speak now!")

        def record_sync():
            try:
                audio_data = sd.rec(
                    int(record_seconds * config.SAMPLE_RATE),
                    samplerate=config.SAMPLE_RATE,
                    channels=config.CHANNELS,
                    dtype="float32"
                )
                sd.wait()
                return audio_data.flatten()
            except Exception as e:
                print(f"[STT Error] Failed to record audio: {e}")
                return np.zeros(int(record_seconds * config.SAMPLE_RATE), dtype=np.float32)

        audio_buffer = await loop.run_in_executor(None, record_sync)
        return audio_buffer

    async def transcribe(self, audio_buffer: np.ndarray) -> str:
        """
        Asynchronously transcribes audio buffer into text using NVIDIA Whisper Large v3 (if enabled) or local Faster-Whisper.
        """
        # Option A: NVIDIA Whisper Large v3 Cloud API
        if (getattr(config, 'USE_NVIDIA_STT', False) or os.getenv("USE_NVIDIA_STT", "false").lower() in ("true", "1")) and getattr(config, 'NVIDIA_API_KEY', ''):
            try:
                import soundfile as sf
                from tools.nvidia_nim_tool import NvidiaNIMClient
                
                temp_wav = os.path.join("scratch", "temp_stt_input.wav")
                os.makedirs("scratch", exist_ok=True)
                sf.write(temp_wav, audio_buffer, config.SAMPLE_RATE)
                
                print("[STT] Transcribing via NVIDIA Whisper Large v3 Cloud API...")
                client = NvidiaNIMClient()
                text = client.transcribe_audio(temp_wav)
                print(f"[STT NVIDIA Whisper v3] Transcribed: \"{text}\"")
                return text
            except Exception as ne:
                print(f"[STT Warning] NVIDIA Whisper Cloud error ({ne}). Falling back to local Faster-Whisper...")

        # Option B: Local Faster-Whisper
        loop = asyncio.get_running_loop()

        def transcribe_sync():
            segments, info = self.model.transcribe(
                audio_buffer,
                beam_size=5,
                language="en",
                initial_prompt=self.initial_prompt,
                vad_filter=True  # Filter out silence
            )
            text = " ".join([segment.text for segment in segments]).strip()
            return text

        transcription = await loop.run_in_executor(None, transcribe_sync)
        print(f"[STT Faster-Whisper] Transcribed: \"{transcription}\"")
        return transcription
