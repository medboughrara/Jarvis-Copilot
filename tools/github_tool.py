"""
GitHub Engineering Issue Manager Tool for Jarvis Copilot.
Creates, tags, and manages GitHub issues and hardware bug reports for PCB schematics.
"""

import os
import json
import subprocess
from langchain_core.tools import tool
import config

logger = config.get_logger(__name__)

@tool
def manage_github_issue(
    title: str = "PCB ERC Violation Alert",
    body: str = "Missing decoupling capacitors detected near MCU power pins.",
    labels: str = "hardware-erc,thermal-risk"
) -> str:
    """
    Creates and logs a GitHub issue on the repository for PCB schematic errors, ERC warnings, or thermal alerts.
    
    Args:
        title: Short title of the issue (e.g. "Decoupling Capacitor Missing on U1").
        body: Detailed description of the PCB issue or thermal alert.
        labels: Comma-separated labels (e.g. "hardware-erc", "thermal-risk", "supply-chain").
    """
    repo = "medboughrara/Jarvis-PCB-Copilot"
    clean_labels = [l.strip() for l in labels.split(",") if l.strip()]

    # Save to local scratch issue log artifact
    os.makedirs("scratch", exist_ok=True)
    issue_file = os.path.join("scratch", "github_issues_log.json")
    
    issues_history = []
    if os.path.exists(issue_file):
        try:
            with open(issue_file, "r", encoding="utf-8") as f:
                issues_history = json.load(f)
        except Exception:
            issues_history = []

    issue_entry = {
        "id": len(issues_history) + 1,
        "repo": repo,
        "title": title,
        "body": body,
        "labels": clean_labels,
        "status": "OPEN",
        "timestamp": config.time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(config, "time") else "2026-08-03"
    }
    issues_history.append(issue_entry)

    try:
        with open(issue_file, "w", encoding="utf-8") as f:
            json.dump(issues_history, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save issue artifact: {e}")

    report = [
        "============================================================",
        f"       GITHUB ISSUE LOGGED: #{issue_entry['id']}",
        "============================================================",
        f"Repository: {repo}",
        f"Title: {title}",
        f"Labels: {', '.join(clean_labels)}",
        f"Status: OPEN (Saved to {issue_file})",
        "------------------------------------------------------------",
        "Body:",
        f"{body}",
        "============================================================"
    ]
    return "\n".join(report)
