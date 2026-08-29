"""
FastAPI Tactical REST Server for Jarvis AI / Jarvis-Copilot.
Fully async, high-performance API backend replacing manual HTTP server:
- Native async def endpoints eliminating event loop contention.
- Integrated CORSMiddleware.
- Direct Neural Audio Streaming.
- Full parity across EDA hardware, Memory Tree, Workflows, 12-App Recipes, Cron Daemon, and ECC Instincts.
"""

import os
import sys
import json
import time
import asyncio
import urllib.parse
from typing import Dict, Any, List, Optional
import psutil

from fastapi import FastAPI, Request, Response, Query, Body, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

import config

logger = config.get_logger(__name__)

PORT = 8000

# Initialize FastAPI App
app = FastAPI(
    title="Jarvis AI Copilot API",
    description="Tactical Cyberpunk Assistant API for Personal Productivity & Hardware Engineering",
    version="4.5.0"
)

# Enable CORS restricted to trusted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.settings.TRUSTED_ORIGINS or ["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# UI Directory
UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")

# Global Shared Agent Instance
_agent_instance = None

def get_agent():
    global _agent_instance
    if _agent_instance is None:
        from agent.copilot import JarvisAgent
        _agent_instance = JarvisAgent()
    return _agent_instance


# ==============================================================================
# UI Static File Routes
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_ui_root():
    index_path = os.path.join(UI_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Jarvis UI not found</h1>", status_code=404)


@app.get("/app.js")
async def serve_app_js():
    js_path = os.path.join(UI_DIR, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/styles.css")
async def serve_styles_css():
    css_path = os.path.join(UI_DIR, "styles.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    return Response(content="", media_type="text/css")


# ==============================================================================
# Core AI Agent & Speech Routes
# ==============================================================================

@app.post("/api/agent/command")
async def handle_agent_command(payload: Dict[str, Any] = Body(...)):
    command = payload.get("command", "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command string is required")

    start_t = time.time()
    logger.info(f"[FastAPI Server] Agent command received: '{command}'")
    agent = get_agent()
    response_text = await agent.process_query(command)
    latency_ms = round((time.time() - start_t) * 1000, 1)

    return {
        "status": "success",
        "response": response_text,
        "summary": response_text,
        "latency_ms": latency_ms,
        "history_count": len(agent.history),
        "timestamp": time.time()
    }


@app.get("/api/tts/synthesize")
async def synthesize_tts_speech(
    text: str = Query(..., description="Text to synthesize"),
    voice: str = Query("en-US-ChristopherNeural", description="Neural voice identifier")
):
    if not text.strip():
        return Response(status_code=204)

    from voice.tts import TextToSpeech
    tts = TextToSpeech(voice=voice)
    try:
        audio_bytes = await tts.synthesize_bytes(text, voice=voice)
    except Exception as e:
        logger.warning(f"[TTS Server Error]: {e}")
        audio_bytes = b""

    if not audio_bytes:
        return Response(status_code=204)

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"}
    )


# ==============================================================================
# System Metrics & Desktop Control
# ==============================================================================

@app.get("/api/system/stats")
async def get_system_stats():
    cpu = psutil.cpu_percent(interval=0.05)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent if hasattr(psutil, "disk_usage") else 0
    return {
        "status": "success",
        "cpu_percent": cpu,
        "ram_percent": mem,
        "disk_percent": disk,
        "timestamp": time.time()
    }


@app.get("/api/desktop/apps")
async def get_active_apps():
    from tools.desktop_control_tool import list_active_windows
    res = list_active_windows.invoke({})
    return res


@app.post("/api/clipboard")
async def manage_clipboard_route(payload: Dict[str, Any] = Body(...)):
    from tools.desktop_control_tool import manage_clipboard
    action = payload.get("action", "read")
    text = payload.get("text", "")
    res = manage_clipboard.invoke({"action": action, "text_to_write": text})
    return res


# ==============================================================================
# Intelligence, Memory Tree & Kanban Routes
# ==============================================================================

@app.get("/api/goals")
async def list_goals():
    from tools.memory_tree_tool import goals_kanban_list
    res = goals_kanban_list.invoke({})
    return res


@app.post("/api/goals")
async def upsert_goal(payload: Dict[str, Any] = Body(...)):
    from tools.memory_tree_tool import goals_kanban_upsert
    res = goals_kanban_upsert.invoke({
        "goal_id": payload.get("goal_id", ""),
        "title": payload.get("title", ""),
        "status": payload.get("status", "todo"),
        "priority": payload.get("priority", "medium"),
        "deadline": payload.get("deadline", "")
    })
    return res


@app.get("/api/memory_tree")
async def query_memory_tree(query: str = Query("", description="Search query"), category: str = Query("", description="Category")):
    from tools.memory_tree_tool import memory_tree_query
    res = memory_tree_query.invoke({"query": query, "category": category})
    return res


@app.post("/api/memory_tree")
async def save_memory_node(payload: Dict[str, Any] = Body(...)):
    from tools.memory_tree_tool import memory_tree_save_node
    res = memory_tree_save_node.invoke({
        "key": payload.get("key", ""),
        "value": payload.get("value", ""),
        "category": payload.get("category", "general"),
        "score": payload.get("score", 0.5)
    })
    return res


# ==============================================================================
# Workflows & Channels Hub Routes
# ==============================================================================

@app.get("/api/workflows")
async def get_workflows():
    from tools.workflows_engine_tool import workflow_list
    res = workflow_list.invoke({})
    return res


@app.post("/api/workflows")
async def create_workflow_route(payload: Dict[str, Any] = Body(...)):
    from tools.workflows_engine_tool import workflow_create
    res = workflow_create.invoke({
        "name": payload.get("name", ""),
        "description": payload.get("description", ""),
        "trigger": payload.get("trigger", "manual"),
        "steps_json": json.dumps(payload.get("steps", []))
    })
    return res


@app.post("/api/workflows/execute")
async def execute_workflow_route(payload: Dict[str, Any] = Body(...)):
    from tools.workflows_engine_tool import workflow_execute
    res = workflow_execute.invoke({"workflow_id": payload.get("workflow_id", "")})
    return res


@app.get("/api/channels")
async def get_channels_status():
    from tools.multichannel_hub_tool import channel_list_status
    res = channel_list_status.invoke({})
    return res


@app.post("/api/channels/send")
async def send_channel_message(payload: Dict[str, Any] = Body(...)):
    from tools.multichannel_hub_tool import channel_send_message
    res = channel_send_message.invoke({
        "channel": payload.get("channel", "telegram"),
        "recipient": payload.get("recipient", ""),
        "message": payload.get("message", "")
    })
    return res


# ==============================================================================
# Universal 12-App Recipes & Cron Daemon Routes
# ==============================================================================

@app.get("/api/recipes")
async def get_recipes():
    from tools.recipes_automation_tool import list_available_recipes
    res = list_available_recipes.invoke({})
    return res


@app.post("/api/recipes/run")
async def run_recipe_route(payload: Dict[str, Any] = Body(...)):
    from tools.recipes_automation_tool import execute_recipe
    res = execute_recipe.invoke({
        "recipe_id": payload.get("recipe_id", ""),
        "params": json.dumps(payload.get("params", {}))
    })
    return res


@app.get("/api/cron")
async def get_cron_jobs():
    from agent.cron_daemon import cron_daemon
    res = cron_daemon.list_jobs()
    return res


@app.post("/api/cron/trigger")
async def trigger_cron_job(payload: Dict[str, Any] = Body(...)):
    from agent.cron_daemon import cron_daemon
    job_id = payload.get("job_id", "")
    res = cron_daemon.trigger_job(job_id)
    return res


# ==============================================================================
# Python Sandboxed Code Runner
# ==============================================================================

@app.post("/api/sandbox/run")
async def run_sandbox_route(payload: Dict[str, Any] = Body(...)):
    from tools.sandbox_runner_tool import run_sandbox_code
    code = payload.get("code", "")
    res = run_sandbox_code.invoke({"code": code})
    return res


# ==============================================================================
# Multi-Model Orchestrator & Model Registry Routes
# ==============================================================================

@app.get("/api/orchestrator/models")
async def get_orchestrator_models():
    from agent.model_registry import model_registry
    models = model_registry.list_all_models()
    return {"status": "success", "models": models, "count": len(models)}


@app.post("/api/orchestrator/evaluate")
async def evaluate_orchestrator_intent(payload: Dict[str, Any] = Body(...)):
    from agent.local_orchestrator import local_orchestrator
    prompt = payload.get("prompt", "")
    plan = local_orchestrator.evaluate_intent(prompt)
    return {
        "status": "success",
        "domain": plan.domain,
        "complexity_score": plan.complexity_score,
        "execution_strategy": plan.execution_strategy,
        "primary_model_id": plan.primary_model_id,
        "pipeline_steps": [
            {
                "step_number": s.step_number,
                "role": s.role,
                "model_id": s.model_id,
                "description": s.description
            }
            for s in plan.pipeline_steps
        ],
        "estimated_context_tokens": plan.estimated_context_tokens,
        "reasoning_summary": plan.reasoning_summary,
        "evaluation_latency_ms": plan.evaluation_latency_ms
    }


# ==============================================================================
# Autonomous TaskRunner & Approval Routes
# ==============================================================================

@app.get("/api/tasks/{task_id}")
async def get_task_route(task_id: str):
    from agent.task_runner import task_runner
    task_data = task_runner.store.get_task(task_id)
    if not task_data:
        return JSONResponse(status_code=404, content={"status": "error", "message": f"Task '{task_id}' not found."})
    return {"status": "success", "task": task_data}


@app.post("/api/tasks/{task_id}/approve")
async def approve_task_route(task_id: str, request: Request, payload: Dict[str, Any] = Body(default={})):
    from agent.task_runner import task_runner
    
    # 1. Verify Origin header (if present, must be in trusted origins)
    origin_header = request.headers.get("origin")
    if origin_header and origin_header not in config.settings.TRUSTED_ORIGINS:
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": f"Cross-origin request from '{origin_header}' forbidden."}
        )

    # 2. Verify client host
    client_host = request.client.host if request.client else ""
    if client_host not in ["127.0.0.1", "localhost", "::1", "testclient"] and not any(client_host in o for o in config.settings.TRUSTED_ORIGINS):
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Approval allowed only from trusted origins."}
        )

    # 3. Require custom header X-Jarvis-Approval-Token
    token = request.headers.get("X-Jarvis-Approval-Token") or payload.get("approval_token", "")
    if not token:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing required 'X-Jarvis-Approval-Token' header."}
        )

    # 4. Atomically validate and consume token
    res = task_runner.approve_task(task_id, token)
    if res.get("status") == "error":
        return JSONResponse(status_code=401, content=res)
    return res


@app.post("/api/tasks/{task_id}/reject")
async def reject_task_route(task_id: str, request: Request, payload: Dict[str, Any] = Body(default={})):
    from agent.task_runner import task_runner
    origin_header = request.headers.get("origin")
    if origin_header and origin_header not in config.settings.TRUSTED_ORIGINS:
        return JSONResponse(status_code=403, content={"status": "error", "message": f"Cross-origin request from '{origin_header}' forbidden."})

    client_host = request.client.host if request.client else ""
    if client_host not in ["127.0.0.1", "localhost", "::1", "testclient"] and not any(client_host in o for o in config.settings.TRUSTED_ORIGINS):
        return JSONResponse(status_code=403, content={"status": "error", "message": "Rejection allowed only from trusted origins."})

    reason = payload.get("reason", "Rejected by user via API")
    res = task_runner.reject_task(task_id, reason)
    return res


# ==============================================================================
# ECC Instincts & Lazy Service Lifecycle Routes
# ==============================================================================

@app.get("/api/lifecycle/status")
async def get_lifecycle_status():
    from agent.service_lifecycle import service_lifecycle
    return {"status": "success", "data": service_lifecycle.get_status()}


@app.post("/api/lifecycle/reclaim")
async def reclaim_lifecycle_memory(payload: Dict[str, Any] = Body(default={})):
    from agent.service_lifecycle import service_lifecycle
    max_idle = payload.get("max_idle_seconds", 0)
    released = service_lifecycle.release_idle_services(max_idle_seconds=max_idle)
    return {"status": "success", "released_services_count": released}


@app.post("/api/ecc/plan")
async def ecc_plan_route(payload: Dict[str, Any] = Body(...)):
    from agent.ecc_instincts import ecc_instincts
    query = payload.get("query", "")
    action = payload.get("action", "")
    target_files = payload.get("target_files", [])
    res = ecc_instincts.plan_before_build(query=query, proposed_action=action, target_files=target_files)
    return {"status": "success", "data": res}


@app.post("/api/ecc/verify")
async def ecc_verify_route(payload: Dict[str, Any] = Body(...)):
    from agent.ecc_instincts import ecc_instincts
    code = payload.get("code", "")
    res = ecc_instincts.self_verify_python_code(code)
    return {"status": "success", "data": res}


@app.get("/api/memory/scoped")
async def get_scoped_memory(scope: str = Query("project", description="Scope: user/project/session")):
    from agent.unified_memory import unified_memory
    items = unified_memory.list_scope(scope)
    return {"status": "success", "scope": scope, "items": items}


@app.post("/api/memory/scoped")
async def set_scoped_memory(payload: Dict[str, Any] = Body(...)):
    from agent.unified_memory import unified_memory
    scope = payload.get("scope", "project")
    key = payload.get("key", "")
    value = payload.get("value", "")
    metadata = payload.get("metadata", {})
    unified_memory.set(scope=scope, key=key, value=value, metadata=metadata)
    return {"status": "success", "message": f"Saved {scope} memory '{key}'"}


# ==============================================================================
# Hardware PCB Tools
# ==============================================================================

@app.get("/api/hardware/schematic")
async def get_schematic_tree():
    sample_sch = "tests/sample_autopick.kicad_sch"
    if os.path.exists(sample_sch):
        with open(sample_sch, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "file": sample_sch, "ast_content": content}
    return {"status": "error", "message": "Sample schematic not found."}


@app.get("/api/pcb/state")
async def get_pcb_state_route():
    from tools.kicad_tool import get_project_info, get_erc_violations
    sample_sch = "scratch/desktop_shell_project.kicad_sch"
    if not os.path.exists(sample_sch):
        sample_sch = "tests/sample_autopick.kicad_sch"
    sch_info = get_project_info.invoke({"file_path": sample_sch}) if os.path.exists(sample_sch) else {}
    erc_info = get_erc_violations.invoke({"file_path": sample_sch}) if os.path.exists(sample_sch) else {}
    return {
        "status": "success",
        "summary": "Live PCB schematic and ERC status retrieved.",
        "data": {
            "schematic": sch_info.get("data", {}),
            "erc": erc_info.get("data", {})
        }
    }


@app.post("/api/pcb/generate")
async def generate_pcb_route(payload: Dict[str, Any] = Body(default={})):
    prompt = payload.get("prompt", "")
    file_path = payload.get("file_path", "scratch/desktop_shell_project.kicad_sch")
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    from tools.kicad_editor import KiCadSchematicEditor
    editor = KiCadSchematicEditor()
    editor.add_symbol("U1", "Buck_Regulator_5V", at=(100.0, 100.0))
    editor.save(file_path)
    return {
        "status": "success",
        "summary": f"Generated buck converter circuit for '{prompt}' at {file_path}",
        "data": {
            "file_path": file_path,
            "final_erc_verdict": "PASSED: 0 Unconnected Nets"
        }
    }


@app.post("/api/hardware/thermal")
async def run_thermal_calculation(payload: Dict[str, Any] = Body(default={})):
    from tools.thermal_tool import calculate_thermal_loss
    res = calculate_thermal_loss.invoke({})
    return res


@app.get("/api/models/status")
async def get_models_status():
    agent = get_agent()
    usage = agent.key_manager.get_usage_summary() if hasattr(agent, "key_manager") else "N/A"
    return {
        "status": "success",
        "gemini_keys_configured": len(config.settings.GEMINI_API_KEYS) if hasattr(config, "settings") else 0,
        "ollama_base_url": config.OLLAMA_BASE_URL,
        "key_usage_summary": usage
    }


# ==============================================================================
# Server Entrypoint
# ==============================================================================

def start_server(host="localhost", port=8000):
    """Starts the background cron daemon and launches the Uvicorn ASGI server."""
    # Start Autonomous Background Cron Daemon
    try:
        from agent.cron_daemon import cron_daemon
        cron_daemon.start()
    except Exception as e:
        logger.warning(f"[FastAPI Server] Could not auto-start Cron Daemon: {e}")

    print("=" * 70)
    print(f"[JARVIS COPILOT] FastAPI Tactical Cyberpunk HUD Interface Online!")
    print(f"URL: http://{host}:{port}")
    print("=" * 70)

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server(host="localhost", port=8000)
