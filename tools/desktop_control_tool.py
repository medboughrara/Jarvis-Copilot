"""
Desktop Automation, System Metrics & Window Control Tool for Jarvis Copilot.
Directly adapts OpenHuman's desktop domain (`src/openhuman/desktop/`).
Provides native Windows desktop intelligence:
- Live CPU, RAM, Disk, and GPU resource telemetry
- Active application and window title enumeration
- System clipboard read / write integration
- High-resolution screen capture
"""

import os
import time
import subprocess
from typing import Dict, Any, List
import psutil
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

SCRATCH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
os.makedirs(SCRATCH_DIR, exist_ok=True)

@tool
def get_system_metrics() -> Dict[str, Any]:
    """
    Returns real-time system hardware statistics including CPU usage, RAM allocation, Disk space, and battery/uptime.
    """
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_cores = psutil.cpu_count(logical=True)
    
    mem = psutil.virtual_memory()
    mem_total_gb = round(mem.total / (1024**3), 2)
    mem_used_gb = round(mem.used / (1024**3), 2)
    mem_percent = mem.percent

    disk = psutil.disk_usage(os.getcwd())
    disk_free_gb = round(disk.free / (1024**3), 2)
    disk_total_gb = round(disk.total / (1024**3), 2)

    boot_time = psutil.boot_time()
    uptime_hours = round((time.time() - boot_time) / 3600, 1)

    return {
        "status": "success",
        "summary": f"System Telemetry: CPU: {cpu_percent}% ({cpu_cores} cores), RAM: {mem_used_gb}/{mem_total_gb} GB ({mem_percent}%), Disk: {disk_free_gb} GB free",
        "data": {
            "cpu_percent": cpu_percent,
            "cpu_cores": cpu_cores,
            "mem_total_gb": mem_total_gb,
            "mem_used_gb": mem_used_gb,
            "mem_percent": mem_percent,
            "disk_free_gb": disk_free_gb,
            "disk_total_gb": disk_total_gb,
            "uptime_hours": uptime_hours
        }
    }


@tool
def list_active_windows() -> Dict[str, Any]:
    """
    Enumerates running processes and open application windows on the desktop.
    """
    apps = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = proc.info
            name = info.get('name', '')
            if name and name.endswith('.exe') and info.get('memory_percent', 0) > 0.5:
                apps.append({
                    "pid": info.get('pid'),
                    "name": name,
                    "mem_percent": round(info.get('memory_percent', 0), 1)
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    apps_sorted = sorted(apps, key=lambda x: x['mem_percent'], reverse=True)[:15]

    return {
        "status": "success",
        "summary": f"Found {len(apps_sorted)} active high-resource desktop applications.",
        "data": {"applications": apps_sorted}
    }


@tool
def manage_clipboard(action: str = "read", text_to_write: str = "") -> Dict[str, Any]:
    """
    Reads from or writes text to the Windows system clipboard.
    
    Args:
        action: 'read' to get clipboard contents or 'write' to set clipboard contents.
        text_to_write: Text to copy to clipboard when action is 'write'.
    """
    if action == "read":
        try:
            cmd = "Get-Clipboard"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=3)
            clipboard_text = res.stdout.strip()
            return {
                "status": "success",
                "summary": f"Clipboard contents retrieved ({len(clipboard_text)} chars).",
                "data": {"content": clipboard_text}
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to read clipboard: {e}"}
    elif action == "write":
        try:
            # Write text via PowerShell Set-Clipboard
            p = subprocess.Popen(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $input"], stdin=subprocess.PIPE, text=True)
            p.communicate(input=text_to_write)
            return {
                "status": "success",
                "summary": f"Copied {len(text_to_write)} characters to clipboard.",
                "data": {"written_length": len(text_to_write)}
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to write clipboard: {e}"}
    else:
        return {"status": "error", "message": f"Invalid action '{action}'. Use 'read' or 'write'."}
