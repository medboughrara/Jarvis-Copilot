"""
Wake Word Detection module using openWakeWord (running on CPU).
Continuously monitors microphone stream until trigger phrase ("jarvis") is detected.
"""

import asyncio
import numpy as np
import openwakeword
from openwakeword.model import Model
import config
import time

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except OSError as e:
    print(f"[Audio Error] sounddevice import failed (PortAudio may be missing): {e}")
    AUDIO_AVAILABLE = False


class WakeWordDetector:
    def __init__(self, target_wakeword: str = config.WAKEWORD_MODEL_NAME, threshold: float = config.WAKEWORD_THRESHOLD):
        self.target_wakeword = target_wakeword
        self.threshold = threshold
        
        # Download default models if needed and load model
        openwakeword.utils.download_models()
        self.oww_model = Model(wakeword_models=[self.target_wakeword], inference_framework="onnx")
        print(f"[WakeWord] openWakeWord initialized listening for '{self.target_wakeword}'.")

    async def wait_for_wakeword(self) -> bool:
        """
        Asynchronously streams microphone audio and blocks until wake word trigger score exceeds threshold.
        """
        if not AUDIO_AVAILABLE:
            print("[WakeWord] Audio device unavailable. Simulating wake word wait for testing...")
            await asyncio.sleep(5)  # Simulate wait in headless environments
            return True

        loop = asyncio.get_running_loop()
        audio_queue = asyncio.Queue()

        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"[WakeWord Audio Callback Status] {status}")
            # Ensure float32 or int16 conversion for openWakeWord (expects int16 numpy array)
            audio_int16 = (indata * 32767).astype(np.int16).flatten()
            loop.call_soon_threadsafe(audio_queue.put_nowait, audio_int16)

        print("[WakeWord] Listening for wake word...")
        
        try:
            # Start sounddevice input stream
            with sd.InputStream(
                samplerate=config.SAMPLE_RATE,
                channels=config.CHANNELS,
                dtype="float32",
                blocksize=config.CHUNK_SIZE,
                callback=audio_callback
            ):
                while True:
                    # Retrieve audio chunk from non-blocking queue
                    chunk = await audio_queue.get()
                    
                    # Predict wake word score (run in executor to keep event loop responsive)
                    prediction = await loop.run_in_executor(
                        None, self.oww_model.predict, chunk
                    )
                    
                    for model_name, score in prediction.items():
                        if score >= self.threshold:
                            print(f"\n[WakeWord] Triggered! ({model_name}: {score:.2f})")
                            self.oww_model.reset()  # Reset internal state buffer
                            return True
        except Exception as e:
            print(f"[WakeWord Error] Failed to open audio stream: {e}")
            await asyncio.sleep(5)
            return True
