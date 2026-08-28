"""
Text-to-Speech module for Jarvis Copilot.
Integrates ultra-realistic Edge-TTS Microsoft Neural Voices, Kokoro-82M 24kHz ONNX,
and NVIDIA Magpie Multilingual Cloud TTS.
"""

import asyncio
import os
import sys
import tempfile
import numpy as np
import config

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except OSError as e:
    AUDIO_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

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


# High-Fidelity Voice Presets
DEFAULT_NEURAL_VOICES = {
    "jarvis": "en-US-ChristopherNeural",       # Deep, authoritative & calm
    "guy": "en-US-GuyNeural",                  # Expressive, natural conversational
    "brian": "en-GB-BrianNeural",              # Sophisticated British accent
    "ryan": "en-GB-RyanNeural",                # Modern British tech
    "aria": "en-US-AriaNeural",                # Clear & professional female
    "jenny": "en-US-JennyNeural",              # Warm & friendly female
    "fr_henri": "fr-FR-HenriNeural",           # French male
    "ar_hedi": "ar-TN-HediNeural"              # Tunisian Arabic
}


class TextToSpeech:
    def __init__(self, voice: str = "en-US-ChristopherNeural"):
        self.voice = DEFAULT_NEURAL_VOICES.get(voice, voice)
        self.kokoro_engine = None
        self._stop_event = asyncio.Event()

        # Check for local Kokoro-82M ONNX model fallback
        model_path = "models/kokoro-v1.0.onnx"
        voices_path = "models/voices-v1.0.bin"

        if KOKORO_ONNX_AVAILABLE and os.path.exists(model_path) and os.path.exists(voices_path):
            try:
                self.kokoro_engine = Kokoro(model_path, voices_path)
            except Exception as e:
                self.kokoro_engine = None

    def stop(self):
        """Stops any active TTS playback immediately."""
        self._stop_event.set()
        if AUDIO_AVAILABLE:
            try:
                sd.stop()
            except Exception:
                pass

    async def synthesize_to_file(self, text: str, output_path: str, voice: str = None) -> str:
        """
        Synthesizes high-fidelity speech audio to an MP3 or WAV file.
        """
        target_voice = DEFAULT_NEURAL_VOICES.get(voice, voice) if voice else self.voice
        clean_text = self._clean_markdown(text)

        if not clean_text:
            return ""

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Primary Option: Edge-TTS Microsoft Neural Voices
        if EDGE_TTS_AVAILABLE:
            try:
                communicate = edge_tts.Communicate(clean_text, voice=target_voice, rate="+4%", pitch="+0Hz")
                await communicate.save(output_path)
                return output_path
            except Exception as e:
                print(f"[TTS Warning] Edge-TTS error ({e}). Trying Kokoro...")

        # Secondary Option: Kokoro-82M Local ONNX
        if self.kokoro_engine and SOUNDFILE_AVAILABLE:
            try:
                samples, sample_rate = self.kokoro_engine.create(clean_text, voice="af_bella", speed=1.05, lang="en-us")
                sf.write(output_path, samples, sample_rate)
                return output_path
            except Exception as e:
                print(f"[TTS Warning] Kokoro synthesis error ({e}).")

        return ""

    async def synthesize_bytes(self, text: str, voice: str = None) -> bytes:
        """
        Synthesizes high-fidelity speech and returns the raw MP3 audio bytes.
        """
        target_voice = DEFAULT_NEURAL_VOICES.get(voice, voice) if voice else self.voice
        clean_text = self._clean_markdown(text)

        if not clean_text:
            return b""

        if EDGE_TTS_AVAILABLE:
            try:
                communicate = edge_tts.Communicate(clean_text, voice=target_voice, rate="+4%", pitch="+0Hz")
                audio_chunks = []
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_chunks.append(chunk["data"])
                return b"".join(audio_chunks)
            except Exception as e:
                print(f"[TTS Stream Warning] Edge-TTS error: {e}")

        # Fallback to file-based synthesis
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            res_path = await self.synthesize_to_file(text, tmp_path, voice=voice)
            if res_path and os.path.exists(res_path):
                with open(res_path, "rb") as f:
                    data = f.read()
                os.remove(res_path)
                return data
        except Exception:
            pass

        return b""

    async def speak(self, text: str, voice: str = None):
        """
        Asynchronously converts text into neural speech and plays out loud via speakers.
        """
        self._stop_event.clear()
        clean_text = self._clean_markdown(text)
        if not clean_text:
            return

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            saved_file = await self.synthesize_to_file(clean_text, tmp_path, voice=voice)
            if saved_file and os.path.exists(saved_file) and SOUNDFILE_AVAILABLE and AUDIO_AVAILABLE:
                data, fs = sf.read(saved_file, dtype='float32')
                duration = len(data) / float(fs)
                sd.play(data, samplerate=fs)
                
                loop = asyncio.get_running_loop()
                end_time = loop.time() + duration
                while loop.time() < end_time:
                    if self._stop_event.is_set():
                        sd.stop()
                        break
                    await asyncio.sleep(0.05)
                sd.stop()
            else:
                self._fallback_sapi_speak(clean_text)
        except Exception as e:
            self._fallback_sapi_speak(clean_text)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _fallback_sapi_speak(self, text: str):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 180)
            engine.say(text)
            engine.runAndWait()
        except Exception:
            if SAPI_AVAILABLE:
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    speaker.Speak(text)
                except Exception:
                    pass

    def _clean_markdown(self, text: str) -> str:
        if not text:
            return ""
        clean = (
            text.replace("```", "")
            .replace("`", "")
            .replace("**", "")
            .replace("*", "")
            .replace("##", "")
            .replace("#", "")
            .replace("- ", "")
            .replace("[]", "")
            .strip()
        )
        return clean
