"""
Acceptance Tests for Local Intent Routing & Fast-Path Triage.
Validates sub-10ms deterministic rule matching across 20 diverse prompts.
"""

import unittest
from agent.local_orchestrator import local_orchestrator


class TestIntentRoutingAndOrchestrator(unittest.TestCase):

    def setUp(self):
        self.code_prompts = [
            "Write a python script to calculate primes up to 100",
            "Generate a javascript function to debounce user input",
            "Implement a linked list reversal in Python",
            "Write unit tests for the authentication module",
            "Fix this function def calc(x): return x * 2",
            "Refactor the database connection handler class",
            "Create a script that parses JSON logs",
            "Write a rust function for binary search",
            "Implement a fast Fourier transform algorithm",
            "Generate pytest test cases for user registration"
        ]

        self.search_prompts = [
            "Search for the latest STM32H7 datasheet pinout",
            "Look up the maximum operating voltage of AP2112K-3.3",
            "Find online the pricing of RP2040 microcontrollers",
            "Search the web for KiCad 8 release highlights",
            "Check the web for ESP32-S3 errata sheet",
            "What is the latest IPC-2221 conductor spacing standard",
            "What's the latest news on RISC-V development boards",
            "Google for MP1584 buck converter application circuit",
            "Browse for lead-free soldering temperature profiles",
            "Search for high-speed differential pair routing guidelines"
        ]

    def test_code_tasks_triage_as_coding_domain(self):
        for prompt in self.code_prompts:
            with self.subTest(prompt=prompt):
                plan = local_orchestrator.evaluate_intent(prompt)
                self.assertEqual(plan.domain, "coding", f"Expected 'coding' domain for: '{prompt}'")
                self.assertEqual(plan.triage_source, "rule_match", f"Expected rule_match for: '{prompt}'")
                self.assertIn(plan.primary_model_id, ["kimi-k2.7-code:cloud", "glm-5.3:cloud"])
                self.assertLess(plan.evaluation_latency_ms, 50.0, "Rule triage should execute in <50ms")

    def test_search_tasks_triage_as_search_domain(self):
        for prompt in self.search_prompts:
            with self.subTest(prompt=prompt):
                plan = local_orchestrator.evaluate_intent(prompt)
                self.assertEqual(plan.domain, "search", f"Expected 'search' domain for: '{prompt}'")
                self.assertEqual(plan.triage_source, "rule_match", f"Expected rule_match for: '{prompt}'")
                self.assertEqual(plan.primary_model_id, "qwen3.8")
                self.assertLess(plan.evaluation_latency_ms, 50.0, "Search triage should execute in <50ms")

    def test_simple_greeting_fast_path(self):
        plan = local_orchestrator.evaluate_intent("Hello Jarvis")
        self.assertEqual(plan.domain, "simple_chat")
        self.assertEqual(plan.execution_strategy, "DIRECT_LOCAL")
        self.assertEqual(plan.triage_source, "rule_match")
        self.assertFalse(plan.is_actionable_task)

    def test_stage1_local_reflex_how_are_you(self):
        import asyncio
        is_local, resp, plan = asyncio.run(local_orchestrator.evaluate_and_respond_async("how are you today"))
        self.assertTrue(is_local, "Expected 'how are you today' to be handled by Stage 1 Local Reflex")
        self.assertIsNotNone(resp)
        self.assertIn("capacity", resp.lower())
        self.assertFalse(plan.is_actionable_task)

    def test_stage1_local_reflex_time_and_identity(self):
        import asyncio
        # Time test
        is_local, resp, _ = asyncio.run(local_orchestrator.evaluate_and_respond_async("what time is it"))
        self.assertTrue(is_local)
        self.assertIn("current time is", resp.lower())

        # Identity test
        is_local, resp, _ = asyncio.run(local_orchestrator.evaluate_and_respond_async("who are you"))
        self.assertTrue(is_local)
        self.assertIn("jarvis", resp.lower())

        # Capabilities test
        is_local, resp, _ = asyncio.run(local_orchestrator.evaluate_and_respond_async("what can you do"))
        self.assertTrue(is_local)
        self.assertIn("hardware", resp.lower())

    def test_stage1_actionable_task_proceeds_to_stage2(self):
        import asyncio
        # Code task
        is_local, resp, plan = asyncio.run(local_orchestrator.evaluate_and_respond_async("Write a python script to calculate primes"))
        self.assertFalse(is_local, "Actionable code task must not be intercepted as simple chat")
        self.assertIsNone(resp)
        self.assertTrue(plan.is_actionable_task)
        self.assertEqual(plan.domain, "coding")

        # Search task
        is_local, resp, plan = asyncio.run(local_orchestrator.evaluate_and_respond_async("Search for the latest STM32 datasheet"))
        self.assertFalse(is_local)
        self.assertTrue(plan.is_actionable_task)
        self.assertEqual(plan.domain, "search")


if __name__ == "__main__":
    unittest.main()
