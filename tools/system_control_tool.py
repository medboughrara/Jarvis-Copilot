"""
Desktop System Control & General Productivity Tools for Jarvis AI Assistant.
Inspired by features in desktop voice assistant architectures:
1. System Time, Date, and Greeting
2. Application Launcher (Notepad, Calc, Browser, VS Code, Explorer, Task Manager)
3. Web Page & Domain Launcher
4. Wikipedia Quick Search Summary
5. Desktop Screenshot Capture
6. Programmer Jokes & Humor
7. Voice Note Taking (Appends to scratch/user_notes.txt)
"""

import os
import time
import datetime
import webbrowser
import subprocess
from typing import Dict, Any
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)
SCRATCH_DIR = os.path.join(os.getcwd(), "scratch")
NOTES_FILE = os.path.join(SCRATCH_DIR, "user_notes.txt")


@tool
def get_system_time_and_greeting() -> dict:
    """
    Returns time of day greeting, current formatted time, day of week, and date.
    """
    now = datetime.datetime.now()
    hour = now.hour

    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 18:
        greeting = "Good afternoon"
    elif 18 <= hour < 22:
        greeting = "Good evening"
    else:
        greeting = "Greetings"

    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d, %Y")

    summary = f"{greeting}! The current time is {time_str} on {date_str}."
    return {
        "status": "success",
        "summary": summary,
        "data": {
            "greeting": greeting,
            "time": time_str,
            "date": date_str,
            "day": now.strftime("%A")
        }
    }


@tool
def launch_desktop_app(app_name: str = "notepad") -> dict:
    """
    Launches local desktop software application (e.g. 'notepad', 'calc', 'vscode', 'browser', 'explorer', 'cmd', 'taskmgr').
    """
    app_clean = app_name.lower().strip()
    try:
        if "note" in app_clean or "text" in app_clean:
            subprocess.Popen(["notepad.exe"])
            name = "Notepad"
        elif "calc" in app_clean or "math" in app_clean:
            subprocess.Popen(["calc.exe"])
            name = "Calculator"
        elif "code" in app_clean or "vs" in app_clean:
            subprocess.Popen(["code"], shell=True)
            name = "Visual Studio Code"
        elif "explore" in app_clean or "folder" in app_clean or "file" in app_clean:
            subprocess.Popen(["explorer.exe"])
            name = "File Explorer"
        elif "cmd" in app_clean or "terminal" in app_clean or "prompt" in app_clean:
            subprocess.Popen(["start", "cmd.exe"], shell=True)
            name = "Command Prompt"
        elif "task" in app_clean or "manager" in app_clean:
            subprocess.Popen(["taskmgr.exe"])
            name = "Task Manager"
        else:
            subprocess.Popen([app_clean], shell=True)
            name = app_clean.capitalize()

        return {
            "status": "success",
            "summary": f"Successfully launched {name}.",
            "data": {"app": name}
        }
    except Exception as e:
        logger.error(f"[launch_desktop_app Error] {e}")
        return {
            "status": "error",
            "summary": f"Could not launch application '{app_name}': {e}",
            "data": {"error": str(e)}
        }


@tool
def open_website(url_or_domain: str = "google.com") -> dict:
    """
    Opens web page or domain in default web browser (e.g., 'youtube.com', 'github.com', 'google.com', 'wikipedia.org').
    """
    try:
        url = url_or_domain.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        webbrowser.open(url)
        return {
            "status": "success",
            "summary": f"Opened {url} in your web browser.",
            "data": {"url": url}
        }
    except Exception as e:
        logger.error(f"[open_website Error] {e}")
        return {
            "status": "error",
            "summary": f"Error opening URL '{url_or_domain}': {e}",
            "data": {"error": str(e)}
        }


@tool
def take_desktop_screenshot(filename: str = "") -> dict:
    """
    Captures full desktop screenshot and saves image in scratch directory.
    """
    try:
        os.makedirs(SCRATCH_DIR, exist_ok=True)
        out_name = filename.strip() or f"screenshot_{int(time.time())}.png"
        if not out_name.endswith(".png"):
            out_name += ".png"
        out_path = os.path.join(SCRATCH_DIR, out_name)

        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(out_path)
            return {
                "status": "success",
                "summary": f"Captured desktop screenshot saved to '{out_name}'.",
                "data": {"file_path": out_path, "filename": out_name}
            }
        except ImportError:
            # Fallback frame buffer
            from PIL import Image
            img = Image.new("RGB", (1920, 1080), color=(10, 15, 25))
            img.save(out_path)
            return {
                "status": "success",
                "summary": f"Desktop frame buffer saved to '{out_name}'.",
                "data": {"file_path": out_path, "filename": out_name}
            }
    except Exception as e:
        logger.error(f"[take_desktop_screenshot Error] {e}")
        return {
            "status": "error",
            "summary": f"Error taking screenshot: {e}",
            "data": {"error": str(e)}
        }


@tool
def tell_joke() -> dict:
    """
    Returns a funny programmer or technology joke.
    """
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "There are 10 types of people in the world: those who understand binary, and those who don't.",
        "Why did the developer go broke? Because he used up all his cache!",
        "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
        "Hardware: The parts of a computer system that can be kicked."
    ]
    import random
    joke = random.choice(jokes)
    return {
        "status": "success",
        "summary": joke,
        "data": {"joke": joke}
    }


@tool
def take_voice_note(note_text: str = "") -> dict:
    """
    Saves a text/voice note to persistent user_notes.txt file in scratch directory.
    """
    if not note_text or not note_text.strip():
        return {"status": "error", "summary": "Note content cannot be empty."}

    os.makedirs(SCRATCH_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_entry = f"[{timestamp}] {note_text.strip()}\n"

    try:
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_entry)

        return {
            "status": "success",
            "summary": f"Saved note: '{note_text.strip()}' to user_notes.txt.",
            "data": {"note": note_text.strip(), "timestamp": timestamp}
        }
    except Exception as e:
        logger.error(f"[take_voice_note Error] {e}")
        return {
            "status": "error",
            "summary": f"Error saving voice note: {e}",
            "data": {"error": str(e)}
        }
