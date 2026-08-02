"""
First-Run Setup Wizard for Jarvis PCB Copilot.
Validates the environment, prerequisites, and models before launching the main loop.
"""

import sys
import os
import subprocess
import importlib.util

def check_python():
    print("[1/6] Checking Python version...")
    if sys.version_info >= (3, 12):
        print("      ✅ Passed: Python 3.12+ detected.")
        return True
    else:
        print(f"      ❌ Failed: Python 3.12+ required (Found {sys.version.split()[0]}).")
        return False

def check_cuda():
    print("[2/6] Checking PyTorch & CUDA availability...")
    if importlib.util.find_spec("torch") is None:
        print("      ❌ Failed: PyTorch is not installed. Run 'uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121'")
        return False
    
    import torch
    if torch.cuda.is_available():
        print(f"      ✅ Passed: CUDA is available (Device: {torch.cuda.get_device_name(0)}).")
        return True
    else:
        print("      ❌ Failed: PyTorch cannot detect a CUDA-capable GPU. Please check drivers or VRAM.")
        return False

def check_ollama():
    print("[3/6] Checking Ollama local service...")
    try:
        import requests
        resp = requests.get("http://localhost:11434/")
        if resp.status_code == 200:
            print("      ✅ Passed: Ollama service is running.")
            return True
        else:
            print("      ❌ Failed: Ollama service returned unexpected status.")
            return False
    except Exception:
        print("      ❌ Failed: Could not connect to Ollama at http://localhost:11434. Is it running?")
        return False

def check_ollama_model(model_name="llama3:8b"):
    print(f"[4/6] Checking for Ollama model '{model_name}'...")
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags")
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            if model_name in models:
                print(f"      ✅ Passed: Model '{model_name}' is available.")
                return True
            else:
                print(f"      ❌ Failed: Model '{model_name}' not found.")
                
                # Auto-pull logic
                user_input = input(f"         Do you want to automatically pull '{model_name}'? [Y/n]: ")
                if user_input.lower() in ['', 'y', 'yes']:
                    print(f"         📥 Pulling '{model_name}'... this may take a while depending on your connection.")
                    subprocess.run(["ollama", "pull", model_name], check=True)
                    print(f"      ✅ Success: Model '{model_name}' pulled successfully.")
                    return True
                else:
                    print("         Please run 'ollama pull {model_name}' manually.")
                    return False
        return False
    except Exception as e:
        print(f"      ❌ Failed: Could not verify models ({e}).")
        return False

def check_microphone():
    print("[5/6] Checking microphone access...")
    if importlib.util.find_spec("sounddevice") is None:
        print("      ❌ Failed: sounddevice package is missing.")
        return False
        
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        if input_devices:
            print(f"      ✅ Passed: Microphone detected (Found {len(input_devices)} input devices).")
            return True
        else:
            print("      ❌ Failed: No microphone input devices found.")
            return False
    except Exception as e:
        print(f"      ❌ Failed: Could not query audio devices ({e}).")
        return False

def check_onnx_weights():
    print("[6/6] Checking Kokoro ONNX model weights...")
    model_path = os.path.join("models", "kokoro-v1.0.onnx")
    voices_path = os.path.join("models", "voices-v1.0.bin")
    
    if os.path.exists(model_path) and os.path.exists(voices_path):
        print("      ✅ Passed: Kokoro-82M ONNX weights found.")
        return True
    else:
        print("      ❌ Failed: Kokoro-82M ONNX models missing in 'models/' directory.")
        print("         Please download 'kokoro-v1.0.onnx' and 'voices-v1.0.bin' into the 'models/' folder.")
        return False

def main():
    print("=" * 65)
    print("      Jarvis PCB Copilot - First-Run Environment Setup Wizard")
    print("=" * 65)
    
    checks = [
        check_python(),
        check_cuda(),
        check_ollama(),
        check_ollama_model(),
        check_microphone(),
        check_onnx_weights()
    ]
    
    print("\n" + "=" * 65)
    if all(checks):
        print("✅ SUCCESS: All system checks passed! You are ready to launch Jarvis.")
        print("   Command: python main.py")
    else:
        print("❌ WARNING: Some checks failed. Please address the issues above before running main.py.")
    print("=" * 65)

if __name__ == "__main__":
    main()
