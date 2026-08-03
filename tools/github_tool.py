"""
GitHub Engineering Issue & Local Issue Tracker Tool for Jarvis Copilot.
Logs PCB schematic issues locally to scratch/github_issues_log.json and posts directly to GitHub API if GITHUB_TOKEN is configured.
"""

import os
import json
import time
import urllib.request
import urllib.parse
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
    Logs a PCB schematic error, ERC warning, or thermal alert locally and posts to GitHub API if GITHUB_TOKEN is set.
    
    Args:
        title: Short title of the issue (e.g. "Decoupling Capacitor Missing on U1").
        body: Detailed description of the PCB issue or thermal alert.
        labels: Comma-separated labels (e.g. "hardware-erc", "thermal-risk", "supply-chain").
    """
    repo = os.getenv("GITHUB_REPOSITORY", "medboughrara/Jarvis-PCB-Copilot")
    clean_labels = [l.strip() for l in labels.split(",") if l.strip()]
    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
    github_token = os.getenv("GITHUB_TOKEN", os.getenv("GH_TOKEN", "")).strip()

    # 1. Local JSON issue log persistence
    os.makedirs("scratch", exist_ok=True)
    issue_file = os.path.join("scratch", "github_issues_log.json")
    
    issues_history = []
    if os.path.exists(issue_file):
        try:
            with open(issue_file, "r", encoding="utf-8") as f:
                issues_history = json.load(f)
        except Exception:
            issues_history = []

    local_id = len(issues_history) + 1
    remote_issue_url = ""
    api_status = "LOCAL_LOGGED"

    # 2. If GITHUB_TOKEN is configured, attempt live API call to GitHub
    if github_token:
        try:
            url = f"https://api.github.com/repos/{repo}/issues"
            payload = json.dumps({
                "title": title,
                "body": f"{body}\n\n*Logged by Jarvis PCB Copilot at {timestamp_str}*",
                "labels": clean_labels
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json",
                    "User-Agent": "Jarvis-PCB-Copilot"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    res_data = json.loads(resp.read().decode("utf-8"))
                    remote_issue_url = res_data.get("html_url", "")
                    local_id = res_data.get("number", local_id)
                    api_status = "GITHUB_API_POSTED"
        except Exception as ge:
            logger.warning(f"Could not post issue to GitHub API: {ge}")
            api_status = f"LOCAL_LOGGED (API Error: {ge})"

    issue_entry = {
        "id": local_id,
        "repo": repo,
        "title": title,
        "body": body,
        "labels": clean_labels,
        "status": api_status,
        "remote_url": remote_issue_url,
        "timestamp": timestamp_str
    }
    issues_history.append(issue_entry)

    try:
        with open(issue_file, "w", encoding="utf-8") as f:
            json.dump(issues_history, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save issue artifact: {e}")

    report = [
        "============================================================",
        f"       GITHUB ISSUE LOGGED: #{local_id}",
        "============================================================",
        f"Repository: {repo}",
        f"Title: {title}",
        f"Labels: {', '.join(clean_labels)}",
        f"Status: {api_status}",
        f"Timestamp: {timestamp_str}"
    ]
    if remote_issue_url:
        report.append(f"GitHub URL: {remote_issue_url}")
    else:
        report.append(f"Local Artifact: scratch/github_issues_log.json")
    report.append("------------------------------------------------------------")
    report.append(f"Body:\n{body}")
    report.append("============================================================")
    return "\n".join(report)
