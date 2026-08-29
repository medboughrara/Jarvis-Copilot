"""
Manual, Human-Operated Submodule Update Utility for Anthropic-Cybersecurity-Skills.

Enforces:
1. Submodule provenance validation (verifies remote URL and git submodule status).
2. Upstream diff summary (lists added/modified/removed skills and scripts/*.py).
3. Risk-tier review warnings for newly added skills (fail-closed to dual_use).
4. Explicit confirmation flag requirement (--confirm) before advancing the pin. Never runs automatically.
"""

import os
import sys
import json
import argparse
import subprocess
from typing import Dict, Any, List, Tuple

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
if sys.stderr.encoding != "utf-8":
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBMODULE_DIR = os.path.join(ROOT_DIR, "data", "security_skills")
INDEX_DIR = os.path.join(ROOT_DIR, "data", "security_skills_index")
RISK_TIERS_PATH = os.path.join(INDEX_DIR, "risk_tiers.json")
EXPECTED_REMOTE_SUBSTRING = "Anthropic-Cybersecurity-Skills"


def run_git(args: List[str], cwd: str = ROOT_DIR) -> Tuple[int, str, str]:
    """Runs a git command and returns (exit_code, stdout, stderr)."""
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def validate_submodule_boundary() -> str:
    """Validates that data/security_skills is a valid git submodule pointing to the expected remote."""
    if not os.path.exists(SUBMODULE_DIR):
        raise RuntimeError(f"[FAIL] Submodule directory does not exist at '{SUBMODULE_DIR}'.")

    # Check git submodule status
    code, out, err = run_git(["submodule", "status", "data/security_skills"])
    if code != 0 or not out:
        raise RuntimeError(f"[FAIL] 'data/security_skills' is not registered as a valid git submodule. Git error: {err}")

    # Check remote URL inside submodule
    code, remote_url, err = run_git(["config", "--get", "remote.origin.url"], cwd=SUBMODULE_DIR)
    if code != 0 or EXPECTED_REMOTE_SUBSTRING.lower() not in remote_url.lower():
        raise RuntimeError(
            f"[FAIL] Submodule remote '{remote_url}' does not match expected repository '{EXPECTED_REMOTE_SUBSTRING}'."
        )

    # Get current commit SHA
    code, head_sha, _ = run_git(["rev-parse", "HEAD"], cwd=SUBMODULE_DIR)
    if code != 0 or not head_sha:
        raise RuntimeError(f"[FAIL] Failed to resolve HEAD commit SHA of submodule.")

    return head_sha


def load_risk_tiers() -> Dict[str, Any]:
    if os.path.exists(RISK_TIERS_PATH):
        with open(RISK_TIERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"skills": {}, "commit_sha": ""}


def analyze_diff(current_sha: str, target_sha: str) -> Dict[str, Any]:
    """Diffs skills and scripts between current and target commit SHAs."""
    code, diff_out, _ = run_git(["diff", "--name-status", current_sha, target_sha], cwd=SUBMODULE_DIR)
    if code != 0:
        return {"error": f"Failed to diff {current_sha}..{target_sha}"}

    lines = diff_out.splitlines() if diff_out else []
    added_skills = set()
    modified_skills = set()
    deleted_skills = set()
    changed_scripts = []

    for line in lines:
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        status, path = parts[0], parts[1]
        
        if path.startswith("skills/"):
            skill_name = path.split("/")[1] if len(path.split("/")) > 1 else ""
            if skill_name:
                if status == "A":
                    added_skills.add(skill_name)
                elif status == "D":
                    deleted_skills.add(skill_name)
                elif status == "M":
                    modified_skills.add(skill_name)

        if "scripts/" in path and path.endswith(".py"):
            changed_scripts.append({"status": status, "path": path})

    return {
        "current_sha": current_sha,
        "target_sha": target_sha,
        "added_skills": sorted(list(added_skills)),
        "modified_skills": sorted(list(modified_skills)),
        "deleted_skills": sorted(list(deleted_skills)),
        "changed_scripts": changed_scripts
    }


def main():
    parser = argparse.ArgumentParser(description="Manual update & verification utility for Anthropic-Cybersecurity-Skills submodule.")
    parser.add_argument("--fetch", action="store_true", help="Fetch latest upstream commits from origin.")
    parser.add_argument("--diff", action="store_true", help="Show diff against latest upstream main.")
    parser.add_argument("--target-sha", type=str, default="", help="Specific target commit SHA to advance pin to.")
    parser.add_argument("--confirm", action="store_true", help="Explicit confirmation flag to advance submodule pin.")
    args = parser.parse_args()

    print("=" * 70)
    print("🔒 [Jarvis Security Skills] Submodule Provenance & Update Utility")
    print("=" * 70)

    try:
        current_sha = validate_submodule_boundary()
        print(f"[PASS] Validated Submodule: data/security_skills")
        print(f"[INFO] Current Pinned Commit: {current_sha}")
    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        sys.exit(1)

    if args.fetch:
        print("[INFO] Fetching upstream origin...")
        code, out, err = run_git(["fetch", "origin"], cwd=SUBMODULE_DIR)
        if code != 0:
            print(f"[ERROR] Fetch failed: {err}", file=sys.stderr)
            sys.exit(1)
        print("[PASS] Fetch completed.")

    # Determine target SHA
    target_sha = args.target_sha
    if not target_sha:
        code, upstream_head, _ = run_git(["rev-parse", "origin/main"], cwd=SUBMODULE_DIR)
        if code == 0 and upstream_head:
            target_sha = upstream_head
        else:
            target_sha = current_sha

    if current_sha == target_sha and not args.diff:
        print(f"[PASS] Submodule is already at the target commit ({current_sha[:12]}). No updates needed.")
        sys.exit(0)

    diff_summary = analyze_diff(current_sha, target_sha)
    print(f"\n--- Submodule Diff Summary ({current_sha[:10]} -> {target_sha[:10]}) ---")
    print(f"Added Skills:    {len(diff_summary.get('added_skills', []))}")
    print(f"Modified Skills: {len(diff_summary.get('modified_skills', []))}")
    print(f"Deleted Skills:  {len(diff_summary.get('deleted_skills', []))}")
    print(f"Changed Scripts: {len(diff_summary.get('changed_scripts', []))}")

    if diff_summary.get("changed_scripts"):
        print("\n⚠️ Changed Executable Scripts (Requires Supply-Chain Review):")
        for sc in diff_summary["changed_scripts"]:
            print(f"  [{sc['status']}] {sc['path']}")

    # Check unclassified skills
    risk_tiers_data = load_risk_tiers()
    reviewed_skills = risk_tiers_data.get("skills", {})
    unreviewed = [s for s in diff_summary.get("added_skills", []) if s not in reviewed_skills]
    if unreviewed:
        print(f"\n🚨 WARNING: {len(unreviewed)} newly added skills have no reviewed tier in risk_tiers.json.")
        print(f"   Pursuant to safety policy, they will FAIL-CLOSED and default to 'dual_use' until human-reviewed.")

    if not args.confirm:
        print("\n" + "=" * 70)
        print("[STOP] Update halted: '--confirm' flag was NOT provided.")
        print("To advance the submodule pin, run:")
        print(f"  python scripts/update_security_skills.py --confirm --target-sha {target_sha}")
        print("=" * 70)
        sys.exit(0)

    # Advance pin
    print(f"\n[INFO] Advancing submodule pin to {target_sha}...")
    code, _, err = run_git(["checkout", target_sha], cwd=SUBMODULE_DIR)
    if code != 0:
        print(f"[ERROR] Failed to checkout {target_sha}: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"[SUCCESS] Submodule pin successfully updated to {target_sha}.")
    print(f"[NOTE] Please review changed scripts and update data/security_skills_index/risk_tiers.json.")


if __name__ == "__main__":
    main()
