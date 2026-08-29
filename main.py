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
import config
from voice.wakeword import WakeWordDetector
from voice.stt import Transcriber
from voice.tts import TextToSpeech
from agent.copilot import JarvisAgent

logger = config.get_logger(__name__)


async def main_loop():
    logger.info("=" * 65)
    logger.info("      JARVIS AI - UNIVERSAL PERSONAL ASSISTANT")
    logger.info("=" * 65)
    logger.info("[System] Initializing voice pipeline & agent engine...")

    # Initialize subsystems
    wakeword_engine = WakeWordDetector()
    stt_engine = Transcriber()
    tts_engine = TextToSpeech()
    agent_engine = JarvisAgent()

    logger.info("[System] Initialization complete. Performing startup briefing...")
    try:
        from tools.system_control_tool import get_startup_briefing
        briefing_res = get_startup_briefing.invoke({})
        briefing_text = briefing_res.get("summary", "System online and ready.")
        logger.info(f"[Jarvis Startup Briefing] > {briefing_text}")
        await tts_engine.speak(briefing_text)
    except Exception as be:
        logger.warning(f"[System] Could not run initial briefing: {be}")

    logger.info("[System] Jarvis is online and listening for wake word 'Jarvis'...")

    tts_task = None
    while True:
        try:
            # Step 1: Continuous background wake word detection
            triggered = await wakeword_engine.wait_for_wakeword()
            
            if triggered:
                # Barge-in: if TTS is playing, cancel it immediately
                if tts_task and not tts_task.done():
                    tts_engine.stop()
                    tts_task.cancel()
                    logger.info("[Barge-in] Interrupted ongoing audio playback.")
                    await asyncio.sleep(0.1)

                # Speak brief acknowledgement audio on wake word
                logger.info("[Jarvis] Wake word recognized! Listening for input...")
                tts_task = asyncio.create_task(tts_engine.speak("Yes? I am listening."))
                
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

                logger.info("[Jarvis] Ready for next command...")

        except asyncio.CancelledError:
            break
        except Exception as turn_err:
            # Per-turn error recovery — logs the error and keeps the voice assistant listening
            logger.exception(f"[Voice Loop Error on Turn]: {turn_err}")
            try:
                tts_task = asyncio.create_task(tts_engine.speak("I apologize, but I encountered an error processing that request. Standing by."))
            except Exception:
                pass
            await asyncio.sleep(0.5)


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

