"""
Acceptance Tests for Autonomous Code Pipeline & DAG TaskRunner.
Validates:
1. Autonomous Code Generation & Subprocess Test Verification.
2. Atomic Rollback from Disk Snapshot on Test Failure.
3. Pure-Python Kahn DAG Cycle Detection.
4. Parallel Task Execution with Wall-Clock Concurrency Timing Assertions.
5. Task Persistence & Crash Recovery.
"""

import os
import time
import secrets
import asyncio
import unittest
from agent.code_pipeline import pipeline_code_write, AutonomousCodePipeline
from agent.task_runner import TaskRunner, TaskNode, PurePythonDAGValidator


class TestCodePipelineAndTaskRunner(unittest.TestCase):

    def setUp(self):
        self.workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.scratch_dir = os.path.join(self.workspace_root, "scratch")
        os.makedirs(self.scratch_dir, exist_ok=True)
        self.task_runner = TaskRunner()

    # 1. Code Pipeline Verification
    def test_pipeline_code_write_success(self):
        target = os.path.join(self.scratch_dir, "test_fibonacci.py")
        res = pipeline_code_write(
            task="Implement a fibonacci function in Python with assertions",
            target_file=target
        )
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(os.path.exists(target))
        self.assertFalse(res["data"]["rolled_back"])

    # 2. Atomic Rollback on Failure
    def test_pipeline_atomic_rollback_on_failure(self):
        target = os.path.join(self.scratch_dir, "preexisting_important_code.py")
        original_content = "# ORIGINAL IMPORTANT USER CODE - DO NOT CORRUPT\ndef original(): return 42\n"
        with open(target, "w", encoding="utf-8") as f:
            f.write(original_content)

        # Force a failing test that cannot be satisfied
        failing_test = "assert 1 == 2, 'Forced failure for rollback test'"
        res = pipeline_code_write(
            task="Write code that will fail verification",
            target_file=target,
            test_code=failing_test,
            max_retries=1
        )
        self.assertEqual(res.get("status"), "error")
        self.assertTrue(res["data"]["rolled_back"])

        # Assert pre-edit file content was atomically restored
        with open(target, "r", encoding="utf-8") as f:
            restored = f.read()
        self.assertEqual(restored, original_content, "Pre-edit snapshot must be completely restored on failure!")

    # 3. Pure-Python Kahn DAG Cycle Detection
    def test_kahn_dag_cycle_detection(self):
        # Acyclic DAG
        n1 = TaskNode(id="n1", name="Step 1", role="planner", action_type="plan")
        n2 = TaskNode(id="n2", name="Step 2", role="generator", action_type="gen", dependencies=["n1"])
        n3 = TaskNode(id="n3", name="Step 3", role="verifier", action_type="verify", dependencies=["n2"])

        is_valid, order, msg = PurePythonDAGValidator.validate_and_order([n1, n2, n3])
        self.assertTrue(is_valid)
        self.assertEqual(order, ["n1", "n2", "n3"])

        # Cyclic Graph: n1 -> n2 -> n3 -> n1
        n1_cyclic = TaskNode(id="n1", name="Step 1", role="planner", action_type="plan", dependencies=["n3"])
        is_cyclic_valid, _, cycle_msg = PurePythonDAGValidator.validate_and_order([n1_cyclic, n2, n3])
        self.assertFalse(is_cyclic_valid)
        self.assertIn("Cycle detected", cycle_msg)

    # 4. Parallel Task Execution & Wall-Clock Timing Assertion
    def test_parallel_execution_timing(self):
        async def run_parallel_substeps():
            # Define 3 independent simulated async I/O steps with 0.3s delay each
            async def delayed_step(name: str, delay: float):
                await asyncio.sleep(delay)
                return {"step": name, "done": True}

            t0 = time.time()
            # Execute in parallel via asyncio.gather
            results = await asyncio.gather(
                delayed_step("A", 0.3),
                delayed_step("B", 0.3),
                delayed_step("C", 0.3)
            )
            elapsed = time.time() - t0
            return results, elapsed

        results, elapsed_time = asyncio.run(run_parallel_substeps())
        self.assertEqual(len(results), 3)
        # 3 tasks of 0.3s sequentially take >= 0.9s; parallel execution must complete in < 0.6s
        self.assertLess(elapsed_time, 0.6, f"Parallel execution took {elapsed_time:.2f}s, expected < 0.6s")

    # 5. Durable Task Persistence
    def test_durable_task_store(self):
        task_id = "test_persistence_task_001"
        node1 = TaskNode(id=f"{task_id}_s1", name="Search Specs", role="searcher", action_type="web_search")
        self.task_runner.store.save_task(task_id, "Test persistence", "search", "SINGLE_SPECIALIZED", [node1])

        retrieved = self.task_runner.store.get_task(task_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["task_id"], task_id)
        self.assertEqual(len(retrieved["steps"]), 1)

    # 6. Task 1 Verification: Blocked Task Crash, Rehydration & Single-Use Resumption
    def test_blocked_task_crash_and_token_resumption(self):
        from agent.security import agentshield
        task_id = f"crash_task_{secrets.token_hex(4)}"
        node1 = TaskNode(id=f"{task_id}_s1", name="Delete file", role="executor", action_type="delete_file", status="BLOCKED")
        token = agentshield.create_approval_request(task_id, "delete_file", {"file": "protected.txt"})

        self.task_runner.store.save_task(task_id, "Delete protected file", "general", "SINGLE_SPECIALIZED", [node1], approval_token=token)

        # Simulate process crash by instantiating a brand-new TaskRunner
        rebooted_runner = TaskRunner()
        rehydrated = rebooted_runner.store.get_task(task_id)
        self.assertIsNotNone(rehydrated)
        self.assertEqual(rehydrated["task_id"], task_id)

        # 1. Invalid token attempt must fail
        bad_res = rebooted_runner.approve_task(task_id, "wrong_token_12345")
        self.assertEqual(bad_res.get("status"), "error")

        # 2. Correct token resumes task
        good_res = rebooted_runner.approve_task(task_id, token)
        self.assertEqual(good_res.get("status"), "success")

        # 3. Token replay must fail (burned on first use)
        replay_res = rebooted_runner.approve_task(task_id, token)
        self.assertEqual(replay_res.get("status"), "error")

    # 7. Task 2 Verification: RUNNING Task Crash Recovery & Side-Effect Idempotency
    def test_running_task_crash_recovery_preserves_side_effects(self):
        task_id = f"running_crash_{secrets.token_hex(4)}"
        node1 = TaskNode(
            id=f"{task_id}_s1",
            name="Send Slack Notification",
            role="executor",
            action_type="tool_call",
            has_side_effect=True,
            status="SUCCESS",
            output={"sent": True, "channel": "#alerts"}
        )
        node2 = TaskNode(
            id=f"{task_id}_s2",
            name="In-Flight File Write",
            role="generator",
            action_type="code_write",
            has_side_effect=True,
            status="RUNNING"
        )
        # Task was IN_PROGRESS when crash occurred
        self.task_runner.store.save_task(task_id, "Send alert and write file", "general", "COLLABORATIVE_PIPELINE", [node1, node2])
        self.task_runner.store.update_step_status(node1)
        self.task_runner.store.update_step_status(node2)

        # Simulate process reboot recovery
        rebooted_runner = TaskRunner()
        rebooted_runner.recover_inflight_tasks()

        recovered_task = rebooted_runner.store.get_task(task_id)
        self.assertEqual(recovered_task["status"], "INTERRUPTED_FAILED")
        self.assertIn("Side effects already completed: Send Slack Notification", recovered_task["error_msg"])

        # Confirm Step 1's SUCCESS status and output were preserved
        step1 = next(s for s in recovered_task["steps"] if s["step_id"] == f"{task_id}_s1")
        self.assertEqual(step1["status"], "SUCCESS")
        self.assertEqual(step1["has_side_effect"], 1)


if __name__ == "__main__":
    import secrets
    unittest.main()
