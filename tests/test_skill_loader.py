"""
Unit tests for agent/skill_loader.py (Jarvis PCB Copilot).
"""

import unittest
from agent.skill_loader import SkillLoader

class TestSkillLoader(unittest.TestCase):
    def test_skill_loader_parsing(self):
        loader = SkillLoader(skills_dir="skills")
        self.assertGreater(len(loader.skills), 0)
        self.assertIn("pcb-thermal-analysis", loader.skills)
        summary = loader.list_skills_summary()
        self.assertIn("pcb-thermal-analysis", summary)

if __name__ == "__main__":
    unittest.main()
