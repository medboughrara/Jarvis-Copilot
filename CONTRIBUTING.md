# Contributing to Jarvis PCB Copilot

Thank you for your interest in contributing!

## Development Setup
1. Clone the repository
2. Run the setup wizard: `python scripts/first_run.py`
3. Make sure to run `python -m unittest discover -s tests` before submitting a PR.

## Architecture
- `agent/`: LangChain orchestration and Ollama prompts.
- `tools/`: Specific tools (KiCad parsing, Web Search, OCR, RAG).
- `voice/`: Wake word detection, Whisper STT, and Kokoro TTS.

## Guidelines
- Avoid heavy GPU dependencies; offload to CPU (like `sentence-transformers` for RAG) where possible to leave VRAM for Ollama.
- Maintain ASCII-safe strings for Windows terminal output.
