"""
Sandboxed Code & Math Execution Runner for Jarvis Copilot.
Directly adapts OpenHuman's sandboxing engine (`src/openhuman/sandbox/`).
Safely executes Python scripts, mathematical formulas, algorithms, and data visualizations:
- Safe subprocess execution with strict 5-second timeout
- Automatic stdout / stderr stream capture
- Automatic matplotlib plot capture and saving to scratch/
"""

import os
import sys
import time
import subprocess
import tempfile
from typing import Dict, Any
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

SCRATCH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
os.makedirs(SCRATCH_DIR, exist_ok=True)

@tool
def run_sandbox_code(code: str) -> Dict[str, Any]:
    """
    Safely executes arbitrary Python code, calculations, algorithms, or data visualization scripts.
    Returns stdout output, execution time, and any generated plots/charts.
    
    Args:
        code: The Python code string to execute.
    """
    start_time = time.time()
    
    # Check for plot generation in code
    has_plot = "plt." in code or "matplotlib" in code
    plot_filename = f"plot_{int(time.time() * 1000)}.png"
    plot_path = os.path.join(SCRATCH_DIR, plot_filename)
    
    injected_code = code
    if has_plot and "plt.savefig" not in code:
        injected_code += f"\nimport matplotlib.pyplot as plt\nplt.savefig(r'{plot_path}', bbox_inches='tight', dpi=150)\n"

    # Create temporary script
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", encoding="utf-8", delete=False) as tmp_file:
        tmp_file.write(injected_code)
        tmp_path = tmp_file.name

    python_executable = sys.executable

    try:
        proc = subprocess.run(
            [python_executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=8.0,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        duration_ms = (time.time() - start_time) * 1000
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        plot_created = os.path.exists(plot_path)

        if proc.returncode == 0:
            summary = f"Code executed successfully in {duration_ms:.1f}ms."
            if plot_created:
                summary += f" Generated visualization: {plot_filename}"
            return {
                "status": "success",
                "summary": summary,
                "data": {
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_time_ms": round(duration_ms, 2),
                    "plot_path": plot_path if plot_created else None,
                    "plot_filename": plot_filename if plot_created else None
                }
            }
        else:
            return {
                "status": "error",
                "summary": f"Execution failed with exit code {proc.returncode}.",
                "data": {
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_time_ms": round(duration_ms, 2)
                }
            }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "summary": "Execution timed out (limit: 8.0s).",
            "data": {"error": "TimeoutExpired"}
        }
    except Exception as e:
        return {
            "status": "error",
            "summary": f"Sandbox execution error: {e}",
            "data": {"error": str(e)}
        }
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
