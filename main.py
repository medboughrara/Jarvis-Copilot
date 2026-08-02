"""
Main Async Execution Loop for Jarvis PCB Copilot (AutoPick / Multiverse AI).

Pipeline Flow:
1. Continuous background wake word detection (`openWakeWord` on CPU).
2. Upon wake word trigger ("hey_jarvis"), activate `Faster-Whisper` STT with custom domain prompt ("AutoPick, Multiverse AI, Sim2Real, servomotors").
3. Process transcribed query through LangChain `JarvisAgent` (Ollama GPU backend).
4. Synthesize agent response via `Kokoro TTS` (CPU) and stream to audio output.
"""

import asyncio
import sys
from voice.wakeword import WakeWordDetector
from voice.stt import Transcriber
from voice.tts import TextToSpeech
from agent.copilot import JarvisAgent


async def main_loop():
    print("=" * 65)
    print("      JARVIS PCB COPILOT - MULTIVERSE AI (AutoPick Project)")
    print("=" * 65)
    print("[System] Initializing voice pipeline & agent engine...")

    # Initialize subsystems
    wakeword_engine = WakeWordDetector()
    stt_engine = Transcriber()
    tts_engine = TextToSpeech()
    agent_engine = JarvisAgent()

    print("\n[System] Initialization complete. Jarvis is online and listening...\n")

    try:
        while True:
            # Step 1: Continuous background wake word detection
            triggered = await wakeword_engine.wait_for_wakeword()
            
            if triggered:
                # Play brief acknowledgement audio or notification
                print("[Jarvis] Wake word recognized! Listening for input...")
                
                # Step 2: Record & Transcribe user speech using Faster-Whisper with domain prompt
                audio_buffer = await stt_engine.record_user_audio(record_seconds=5.0)
                transcription = await stt_engine.transcribe(audio_buffer)

                if not transcription.strip():
                    await tts_engine.speak("I didn't hear any command. Standing by.")
                    continue

                # Step 3: Send transcription to LangChain agent
                agent_response = await agent_engine.process_query(transcription)

                # Step 4: Convert agent text response to Kokoro TTS audio playback
                await tts_engine.speak(agent_response)

                print("\n[Jarvis] Ready for next command...\n")

    except KeyboardInterrupt:
        print("\n[System] Jarvis shutting down gracefully. Goodbye!")
    except Exception as e:
        print(f"\n[System Error] Unexpected exception in main execution loop: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Windows Python 3.12 selector event loop policy fix
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main_loop())
