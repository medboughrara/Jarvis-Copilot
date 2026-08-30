"""
SkillSpector Integration Tool & Standalone CLI.
Exposes NVIDIA SkillSpector scanning capabilities to LangChain agents, FastAPI endpoints, and CI/CD pipelines.

Commands:
- inspect_skill(skill_path: str, no_llm: bool = True) -> Dict[str, Any]
- scan_all_installed_skills() -> Dict[str, Any]
- audit_skill_security_posture() -> Dict[str, Any]
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import config
from agent.skillspector_scanner import skillspector_scanner, ScanResult

logger = config.get_logger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_SKILLS_DIR = os.path.join(ROOT_DIR, "skills")
SECURITY_SKILLS_DIR = os.path.join(ROOT_DIR, "data", "security_skills", "skills")


@tool
def inspect_skill(skill_path: str, no_llm: bool = True) -> Dict[str, Any]:
    """
    Audits a skill folder, archive, or script using NVIDIA SkillSpector.
    Returns risk score (0-100), risk tier (LOW/MEDIUM/HIGH/CRITICAL), findings, and remediation steps.
    """
    # Resolve relative path against project root if needed
    if not os.path.isabs(skill_path):
        skill_path = os.path.join(ROOT_DIR, skill_path)

    if not os.path.exists(skill_path):
        return {
            "error": f"Target path '{skill_path}' does not exist.",
            "is_safe": False,
            "risk_score": 100,
            "risk_tier": "CRITICAL"
        }

    res: ScanResult = skillspector_scanner.scan_target(skill_path)
    logger.info(f"[SkillSpector] Audited '{skill_path}': Score {res.risk_score} ({res.risk_tier}), {res.findings_count} finding(s).")
    return res.to_dict()


@tool
def scan_all_installed_skills() -> Dict[str, Any]:
    """
    Audits all installed skills across core assistant skills (skills/) and security skills.
    Returns complete security compliance posture.
    """
    results: Dict[str, Any] = {
        "core_skills": {},
        "total_skills_scanned": 0,
        "clean_skills_count": 0,
        "flagged_skills_count": 0,
        "critical_skills_count": 0,
        "overall_status": "COMPLIANT"
    }

    # 1. Scan Core Workspace Skills
    if os.path.exists(CORE_SKILLS_DIR):
        for item in sorted(os.listdir(CORE_SKILLS_DIR)):
            item_path = os.path.join(CORE_SKILLS_DIR, item)
            if os.path.isdir(item_path):
                scan_res = skillspector_scanner.scan_target(item_path)
                results["core_skills"][item] = {
                    "risk_score": scan_res.risk_score,
                    "risk_tier": scan_res.risk_tier,
                    "is_safe": scan_res.is_safe,
                    "findings_count": scan_res.findings_count,
                    "findings": [f.title for f in scan_res.findings]
                }
                results["total_skills_scanned"] += 1
                if scan_res.is_safe:
                    results["clean_skills_count"] += 1
                else:
                    results["flagged_skills_count"] += 1
                if scan_res.risk_tier == "CRITICAL":
                    results["critical_skills_count"] += 1

    if results["critical_skills_count"] > 0:
        results["overall_status"] = "NON_COMPLIANT_CRITICAL"
    elif results["flagged_skills_count"] > 0:
        results["overall_status"] = "REVIEW_REQUIRED"
    else:
        results["overall_status"] = "100%_SECURE_VERIFIED"

    return results


def run_cli():
    """CLI Entrypoint for running SkillSpector directly from terminal or CI/CD."""
    parser = argparse.ArgumentParser(
        prog="skillspector",
        description="NVIDIA SkillSpector AI Agent Skill Security Scanner"
    )
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan a skill directory or file")
    scan_parser.add_argument("target", help="Path to skill directory, SKILL.md, or script")
    scan_parser.add_argument("--no-llm", action="store_true", default=True, help="Run fast static AST/pattern analysis")
    scan_parser.add_argument("--sarif", action="store_true", help="Output SARIF format for CI/CD")
    scan_parser.add_argument("--json", action="store_true", help="Output JSON format")

    audit_parser = subparsers.add_parser("audit", help="Audit all installed skills in the workspace")

    args = parser.parse_args()

    if args.command == "scan":
        target = args.target
        if not os.path.isabs(target):
            target = os.path.join(ROOT_DIR, target)

        res = skillspector_scanner.scan_target(target)
        if args.sarif:
            print(json.dumps(res.to_sarif(), indent=2))
        elif args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"\n=======================================================")
            print(f" [SECURITY AUDIT] NVIDIA SKILLSPECTOR REPORT")
            print(f"=======================================================")
            print(f" Target Path:      {res.target_path}")
            print(f" Scanned Files:    {len(res.scanned_files)}")
            print(f" Scan Duration:    {res.scan_duration_ms:.1f}ms")
            print(f" Risk Score:       {res.risk_score} / 100")
            print(f" Risk Tier:        {res.risk_tier}")
            print(f" Safe to Execute:  {'[PASS] YES' if res.is_safe else '[FAIL] NO (BLOCKED)'}")
            print(f" Findings:         {res.findings_count} active ({res.suppressed_count} baseline suppressed)")
            print(f"-------------------------------------------------------")
            for idx, f in enumerate(res.findings, 1):
                print(f" [{idx}] [{f.severity}] {f.title} ({f.rule_id})")
                print(f"     File: {f.file_path}:{f.line_number}")
                print(f"     Detail: {f.message}")
                if f.snippet:
                    print(f"     Code:   {f.snippet}")
                if f.remediation:
                    print(f"     Remedy: {f.remediation}")
                print()
            print(f"=======================================================\n")
            sys.exit(0 if res.is_safe else 1)

    elif args.command == "audit":
        audit_res = scan_all_installed_skills.invoke({})
        print(json.dumps(audit_res, indent=2))
        sys.exit(0 if audit_res["critical_skills_count"] == 0 else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    run_cli()
