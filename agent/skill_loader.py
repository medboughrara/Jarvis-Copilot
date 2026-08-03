"""
Standardized SKILL.md Playbook Loader for Jarvis Copilot.
Scans skills/ directory, parses YAML frontmatter, and registers dynamic hardware engineering playbooks.
"""

import os
import re

class SkillLoader:
    """Scans and loads AAS-style SKILL.md playbooks from skills/ directory."""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self.skills = {}
        self.reload_skills()

    def reload_skills(self):
        """Scans skills/ directory and parses all SKILL.md files."""
        self.skills = {}
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir, exist_ok=True)
            return

        for root, _, files in os.walk(self.skills_dir):
            for file in files:
                if file.lower() == "skill.md":
                    full_path = os.path.join(root, file)
                    skill_data = self._parse_skill_file(full_path)
                    if skill_data:
                        self.skills[skill_data["name"]] = skill_data

    def _parse_skill_file(self, filepath: str) -> dict | None:
        """Parses YAML frontmatter and markdown body from SKILL.md."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract YAML frontmatter delimited by ---
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if not match:
                return None

            frontmatter_raw = match.group(1)
            markdown_body = match.group(2).strip()

            name = ""
            description = ""
            keywords = []

            for line in frontmatter_raw.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip().strip('"').strip("'")
                    if k == "name":
                        name = v
                    elif k == "description":
                        description = v
                    elif k == "keywords":
                        keywords = [kw.strip().strip('"').strip("'") for kw in v.strip("[]").split(",") if kw.strip()]

            if not name:
                name = os.path.basename(os.path.dirname(filepath))

            return {
                "name": name,
                "description": description,
                "keywords": keywords,
                "filepath": filepath,
                "instructions": markdown_body
            }
        except Exception as e:
            print(f"[SkillLoader Warning] Could not parse {filepath}: {e}")
            return None

    def get_skill_instructions(self, query: str) -> str:
        """Matches query against loaded skills using full skill name, name phrase, or explicit keywords."""
        query_lower = query.lower()
        matched_instructions = []

        for name, data in self.skills.items():
            name_lower = name.lower()
            name_phrase = name_lower.replace("-", " ")
            keywords = data.get("keywords", [])

            is_match = False
            if name_lower in query_lower or name_phrase in query_lower:
                is_match = True
            elif keywords:
                if any(kw.lower() in query_lower for kw in keywords if len(kw.strip()) > 3):
                    is_match = True

            if is_match:
                matched_instructions.append(f"### SKILL PLAYBOOK: {name.upper()}\n{data['instructions']}")

        return "\n\n".join(matched_instructions)

    def list_skills_summary(self) -> str:
        """Returns summary table of all loaded SKILL.md playbooks."""
        if not self.skills:
            return "No custom SKILL.md playbooks currently loaded in skills/."

        lines = [
            "============================================================",
            "        JARVIS LOADED SKILL PLAYBOOKS (AAS CORE)",
            "============================================================",
            f"{'Skill Name':<28} | {'Description'}",
            "------------------------------------------------------------"
        ]

        for name, data in self.skills.items():
            desc = data['description'][:45] + "..." if len(data['description']) > 45 else data['description']
            lines.append(f"{name:<28} | {desc}")

        lines.append("============================================================")
        return "\n".join(lines)
