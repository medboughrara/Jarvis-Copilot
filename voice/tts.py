"""
Text-to-Speech module for Jarvis Copilot using Kokoro-82M.
Synthesizes high-quality, human-like voice audio at 24kHz using ONNX Runtime CPU execution.
"""

import asyncio
import os
import sys
import numpy as np
import sounddevice as sd
import config

try:
    from kokoro_onnx import Kokoro
    KOKORO_ONNX_AVAILABLE = True
except ImportError:
    KOKORO_ONNX_AVAILABLE = False

try:
    import win32com.client
    SAPI_AVAILABLE = True
except ImportError:
    SAPI_AVAILABLE = False


class TextToSpeech:
    def __init__(self, voice: str = config.TTS_VOICE):
        self.voice = voice
        self.sample_rate = 24000  # High-quality 24kHz audio synthesis
        self.kokoro_engine = None
        
        # Check for downloaded Kokoro-82M ONNX model files
        model_path = "models/kokoro-v1.0.onnx"
        voices_path = "models/voices-v1.0.bin"

        if KOKORO_ONNX_AVAILABLE and os.path.exists(model_path) and os.path.exists(voices_path):
            try:
                print(f"[TTS] Initializing Kokoro-82M (24kHz Human-Like Voice Synthesis)...")
                self.kokoro_engine = Kokoro(model_path, voices_path)
                print(f"[TTS] Kokoro-82M ready with voice: '{self.voice}' at 24000Hz.")
            except Exception as e:
                print(f"[TTS Warning] Kokoro-82M load error ({e}). Using SAPI5 fallback.")
                self.kokoro_engine = None
        else:
            print("[TTS Warning] Kokoro-82M model files not found. Using fallback engine.")

    async def speak(self, text: str):
        """
        Asynchronously converts text into 24kHz human-like Kokoro-82M speech audio and plays out loud via speakers.
        """
        if not text or not text.strip():
            return

        # Clean markdown formatting for voice synthesis
        clean_text = text.replace("*", "").replace("`", "").replace("#", "").replace("- ", "").strip()
        safe_print_text = clean_text.encode('ascii', errors='ignore').decode('ascii')
        print(f"\n[Kokoro-82M Speaking 24kHz]: \"{safe_print_text}\"")

        loop = asyncio.get_running_loop()

        def play_audio_sync():
            # Primary: Kokoro-82M 24kHz high-quality neural voice synthesis
            if self.kokoro_engine:
                try:
                    # Synthesize 24kHz audio waveform (using af_bella voice)
                    samples, sample_rate = self.kokoro_engine.create(
                        clean_text,
                        voice="af_bella",
                        speed=config.TTS_SPEED,
                        lang="en-us"
                    )
                    # Play 24kHz audio through laptop speakers
                    sd.play(samples, samplerate=sample_rate)
                    sd.wait()
                    return
                except Exception as e:
                    print(f"[TTS Error] Kokoro-82M synthesis error ({e}). Falling back to SAPI5.")

            # Secondary Fallback: Windows SAPI5
            if SAPI_AVAILABLE:
                try:
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    speaker.Speak(clean_text)
                    return
                except Exception as e:
                    print(f"[TTS SAPI Error] {e}")

            print(f"[TTS Audio Stream] {safe_print_text}")

        await loop.run_in_executor(None, play_audio_sync)
