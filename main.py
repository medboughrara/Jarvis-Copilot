"""
Main Async Execution Loop for Jarvis PCB Copilot.

Pipeline Flow:
1. Continuous background wake word detection (`openWakeWord` on CPU).
2. Upon wake word trigger ("jarvis"), activate `Faster-Whisper` STT.
3. Process transcribed query through LangChain `JarvisAgent`.
4. Synthesize agent response via `Kokoro TTS` (CPU) and stream to audio output.
"""

import os
import sys
import asyncio
from voice.wakeword import WakeWordDetector
from voice.stt import Transcriber
from voice.tts import TextToSpeech
from agent.copilot import JarvisAgent


async def main_loop():
    print("=" * 65)
    print("      JARVIS AI - UNIVERSAL PERSONAL ASSISTANT")
    print("=" * 65)
    print("[System] Initializing voice pipeline & agent engine...")

    # Initialize subsystems
    wakeword_engine = WakeWordDetector()
    stt_engine = Transcriber()
    tts_engine = TextToSpeech()
    agent_engine = JarvisAgent()

    print("\n[System] Initialization complete. Jarvis is online and listening...\n")

    try:
        tts_task = None
        while True:
            # Step 1: Continuous background wake word detection
            triggered = await wakeword_engine.wait_for_wakeword()
            
            if triggered:
                # Barge-in: if TTS is playing, cancel it immediately
                if tts_task and not tts_task.done():
                    tts_engine.stop()
                    tts_task.cancel()
                    print("\n[Barge-in] Interrupted ongoing audio playback.")
                    await asyncio.sleep(0.1)

                # Play brief acknowledgement audio or notification
                print("[Jarvis] Wake word recognized! Listening for input...")
                
                # Step 2: Record & Transcribe user speech using Faster-Whisper with domain prompt
                audio_buffer = await stt_engine.record_user_audio(record_seconds=5.0)
                transcription = await stt_engine.transcribe(audio_buffer)

                if not transcription.strip():
                    tts_task = asyncio.create_task(tts_engine.speak("I didn't hear any command. Standing by."))
                    continue

                # Quick short-circuit for stop/cancel commands
                transcription_lower = transcription.lower().strip().strip(".!")
                if transcription_lower in ["stop", "cancel", "never mind", "nevermind", "quiet", "silence", "shut up"]:
                    tts_task = asyncio.create_task(tts_engine.speak("Understood."))
                    continue

                # Step 3: Send transcription to LangChain agent
                agent_response = await agent_engine.process_query(transcription)

                # Step 4: Convert agent text response to Kokoro TTS audio playback
                tts_task = asyncio.create_task(tts_engine.speak(agent_response))

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

    # Check for --ui / --web CLI flags
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["--ui", "--web", "-u", "-w"]:
        from web_server import start_server
        start_server(host="localhost", port=8000)
    else:
        asyncio.run(main_loop())

