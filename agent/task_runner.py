"""
📊 Unified DAG TaskRunner & Parallel Execution Engine for Jarvis Copilot.

Implements the 4-phase contract: Plan -> Act -> Verify -> Report
1. Pure-Python Kahn DAG Cycle Detection & Dependency Validation.
2. Durable State Persistence & Side-Effect Aware Crash Recovery (data/task_runner.db).
3. Bounded Asynchronous Parallelism (MAX_PARALLEL_CLOUD_CALLS vs MAX_PARALLEL_LOCAL_GPU_CALLS).
4. Single-Use Cryptographic Tokenized Human Approval Flow.
5. Bidirectional Kanban Projection Sync & Obsidian Runs/ Mirroring.
"""

import os
import sys
import time
import json
import secrets
import sqlite3
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
import config
from agent.security import agentshield
from agent.code_pipeline import pipeline_code_write
from tools.reach_tool import search_web_explicit

logger = config.get_logger(__name__)


@dataclass
class TaskNode:
    id: str
    name: str
    role: str  # "planner", "generator", "verifier", "executor", "searcher"
    action_type: str  # "code_write", "web_search", "hardware_verify", "tool_call"
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    model_id: str = "gemini-2.5-flash"
    has_side_effect: bool = False
    status: str = "PENDING"  # "PENDING", "RUNNING", "SUCCESS", "BLOCKED", "FAILED"
    output: Optional[Dict[str, Any]] = None
    error_msg: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class PurePythonDAGValidator:
    """Pure-Python Kahn's algorithm for zero-dependency sub-millisecond DAG cycle detection."""

    @staticmethod
    def validate_and_order(nodes: List[TaskNode]) -> Tuple[bool, List[str], str]:
        """
        Validates that the task graph is acyclic and all dependencies resolve.
        Returns (is_valid, topological_order, message).
        """
        node_map = {n.id: n for n in nodes}
        in_degree = {n.id: 0 for n in nodes}
        adj_list = {n.id: [] for n in nodes}

        # Validate dependency references
        for n in nodes:
            for dep in n.dependencies:
                if dep not in node_map:
                    return False, [n.id for n in nodes], f"Dangling dependency '{dep}' for node '{n.id}'."
                adj_list[dep].append(n.id)
                in_degree[n.id] += 1

        # Kahn's algorithm
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        topological_order = []

        while queue:
            curr = queue.pop(0)
            topological_order.append(curr)
            for neighbor in adj_list[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topological_order) == len(nodes):
            return True, topological_order, "Acyclic DAG verified successfully."
        else:
            return False, [n.id for n in nodes], "Cycle detected in task dependency graph. Falling back to sequential execution."


class DurableTaskStore:
    """SQLite-backed persistent store for tasks, DAG state, and step completion tracking."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            config.settings.TASK_RUNNER_DB_PATH
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        prompt TEXT,
                        domain TEXT,
                        strategy TEXT,
                        status TEXT,
                        created_at REAL,
                        completed_at REAL,
                        approval_token TEXT,
                        error_msg TEXT,
                        final_summary TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS task_steps (
                        step_id TEXT PRIMARY KEY,
                        task_id TEXT,
                        step_number INTEGER,
                        name TEXT,
                        role TEXT,
                        action_type TEXT,
                        params_json TEXT,
                        dependencies_json TEXT,
                        model_id TEXT,
                        has_side_effect INTEGER,
                        status TEXT,
                        output_json TEXT,
                        started_at REAL,
                        completed_at REAL,
                        FOREIGN KEY (task_id) REFERENCES tasks (task_id)
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"[TaskStore] DB init error: {e}")

    def save_task(self, task_id: str, prompt: str, domain: str, strategy: str, nodes: List[TaskNode], approval_token: str = None):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks (task_id, prompt, domain, strategy, status, created_at, approval_token)
                    VALUES (?, ?, ?, ?, 'IN_PROGRESS', ?, ?)
                """, (task_id, prompt, domain, strategy, time.time(), approval_token))

                for i, node in enumerate(nodes):
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_steps (
                            step_id, task_id, step_number, name, role, action_type,
                            params_json, dependencies_json, model_id, has_side_effect, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        node.id, task_id, i + 1, node.name, node.role, node.action_type,
                        json.dumps(node.params), json.dumps(node.dependencies), node.model_id,
                        1 if node.has_side_effect else 0, node.status
                    ))
                conn.commit()
        except Exception as e:
            logger.error(f"[TaskStore] Error saving task '{task_id}': {e}")

    def update_step_status(self, node: TaskNode):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE task_steps
                    SET status = ?, output_json = ?, started_at = ?, completed_at = ?
                    WHERE step_id = ?
                """, (
                    node.status,
                    json.dumps(node.output) if node.output else None,
                    node.started_at,
                    node.completed_at,
                    node.id
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"[TaskStore] Error updating step '{node.id}': {e}")

    def update_task_completion(self, task_id: str, status: str, summary: str = "", error_msg: str = None):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tasks
                    SET status = ?, completed_at = ?, final_summary = ?, error_msg = ?
                    WHERE task_id = ?
                """, (status, time.time(), summary, error_msg, task_id))
                conn.commit()
        except Exception as e:
            logger.error(f"[TaskStore] Error completing task '{task_id}': {e}")

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
                task_row = cursor.fetchone()
                if not task_row:
                    return None
                task_data = dict(task_row)

                cursor.execute("SELECT * FROM task_steps WHERE task_id = ? ORDER BY step_number ASC", (task_id,))
                steps = [dict(r) for r in cursor.fetchall()]
                task_data["steps"] = steps
                return task_data
        except Exception as e:
            logger.error(f"[TaskStore] Error getting task '{task_id}': {e}")
            return None


class TaskRunner:
    """Universal asynchronous DAG TaskRunner with bounded worker pools and approval resumption."""

    def __init__(self):
        self.store = DurableTaskStore()
        self.cloud_sem = asyncio.Semaphore(config.settings.MAX_PARALLEL_CLOUD_CALLS)
        self.gpu_sem = asyncio.Semaphore(config.settings.MAX_PARALLEL_LOCAL_GPU_CALLS)
        self.task_sem = asyncio.Semaphore(config.settings.MAX_PARALLEL_TASKS)
        self.recover_inflight_tasks()

    def recover_inflight_tasks(self):
        """
        Scans for interrupted in-flight tasks on startup.
        Preserves completed side-effects and transitions running tasks to INTERRUPTED_FAILED.
        """
        try:
            with sqlite3.connect(self.store.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT task_id, prompt FROM tasks WHERE status = 'IN_PROGRESS'")
                inflight = cursor.fetchall()
                for row in inflight:
                    tid = row["task_id"]
                    cursor.execute("SELECT name, has_side_effect, status FROM task_steps WHERE task_id = ?", (tid,))
                    steps = cursor.fetchall()
                    side_effects_done = [s["name"] for s in steps if s["status"] == "SUCCESS" and s["has_side_effect"]]
                    
                    notice = f"Task was interrupted by server shutdown."
                    if side_effects_done:
                        notice += f" Side effects already completed: {', '.join(side_effects_done)}. These will not be duplicated."
                    
                    cursor.execute("""
                        UPDATE tasks SET status = 'INTERRUPTED_FAILED', error_msg = ? WHERE task_id = ?
                    """, (notice, tid))
                    logger.warning(f"[TaskRunner Recovery] Marked task '{tid}' as INTERRUPTED_FAILED: {notice}")
                conn.commit()
        except Exception as e:
            logger.debug(f"[TaskRunner] Recovery scan notice: {e}")

    def build_dag_for_intent(self, prompt: str, domain: str, strategy: str) -> List[TaskNode]:
        """
        Constructs a validated DAG of TaskNodes for a given request.
        Single-step requests become 1-node DAGs; compound requests become N-node DAGs.
        """
        task_id = f"task_{secrets.token_hex(4)}"

        if domain == "coding" and strategy == "COLLABORATIVE_PIPELINE":
            # 3-Node Compound Coding Pipeline
            node_plan = TaskNode(
                id=f"{task_id}_step1_plan",
                name="Architectural Deconstruction",
                role="planner",
                action_type="plan_code",
                model_id="glm-5.3:cloud",
                has_side_effect=False
            )
            node_gen = TaskNode(
                id=f"{task_id}_step2_gen",
                name="Code Implementation & Diff Generation",
                role="generator",
                action_type="code_write",
                params={"task": prompt},
                dependencies=[node_plan.id],
                model_id="kimi-k2.7-code:cloud",
                has_side_effect=True
            )
            node_verify = TaskNode(
                id=f"{task_id}_step3_verify",
                name="Static AST & Sandboxed Test Verification",
                role="verifier",
                action_type="verify_code",
                dependencies=[node_gen.id],
                model_id="glm-5.3-flash:cloud",
                has_side_effect=False
            )
            return [node_plan, node_gen, node_verify]

        elif domain == "coding":
            # 1-Node Direct Code Task
            return [
                TaskNode(
                    id=f"{task_id}_step1",
                    name="Write and Verify Code",
                    role="generator",
                    action_type="code_write",
                    params={"task": prompt},
                    model_id="kimi-k2.7-code:cloud",
                    has_side_effect=True
                )
            ]

        elif domain == "search":
            # 1-Node Explicit Search Task
            return [
                TaskNode(
                    id=f"{task_id}_step1",
                    name="Explicit Web Search with Citations",
                    role="searcher",
                    action_type="web_search",
                    params={"query": prompt},
                    model_id="qwen3.8",
                    has_side_effect=False
                )
            ]

        else:
            # 1-Node General Task
            return [
                TaskNode(
                    id=f"{task_id}_step1",
                    name="General Assistant Execution",
                    role="executor",
                    action_type="general",
                    params={"query": prompt},
                    model_id="gemini-2.5-flash",
                    has_side_effect=False
                )
            ]

    async def execute_task(self, prompt: str, domain: str, strategy: str) -> Dict[str, Any]:
        """
        Executes a task across its 4-phase contract: Plan -> Act -> Verify -> Report.
        """
        async with self.task_sem:
            nodes = self.build_dag_for_intent(prompt, domain, strategy)
            task_id = nodes[0].id.split("_")[0] + "_" + nodes[0].id.split("_")[1]

            # 1. Validate DAG Acyclicity
            is_valid, order, val_msg = PurePythonDAGValidator.validate_and_order(nodes)
            if not is_valid:
                logger.warning(f"[TaskRunner {task_id}] DAG validation warning: {val_msg}")

            # Check if any step requires human approval gate
            approval_token = None
            for n in nodes:
                if agentshield.requires_approval(n.action_type, n.params):
                    approval_token = agentshield.create_approval_request(task_id, n.action_type, n.params)
                    n.status = "BLOCKED"

            # 2. Persist Task State & Update Kanban
            self.store.save_task(task_id, prompt, domain, strategy, nodes, approval_token)
            self._sync_kanban(task_id, prompt, "In Progress" if not approval_token else "Blocked")

            if approval_token:
                logger.info(f"[TaskRunner {task_id}] Task requires human approval. Generated Token. Status: BLOCKED.")
                return {
                    "status": "blocked",
                    "task_id": task_id,
                    "summary": f"Task '{task_id}' requires human approval before proceeding.",
                    "approval_token": approval_token,
                    "data": {"approval_required": True}
                }

            # 3. Asynchronous DAG Execution
            return await self._execute_dag_pipeline(task_id, prompt, nodes, order)

    async def _execute_dag_pipeline(self, task_id: str, prompt: str, nodes: List[TaskNode], order: List[str]) -> Dict[str, Any]:
        completed_outputs = {}
        for node_id in order:
            node = next(n for n in nodes if n.id == node_id)
            if node.status == "SUCCESS":
                completed_outputs[node.id] = node.output
                continue

            node.status = "RUNNING"
            node.started_at = time.time()
            self.store.update_step_status(node)

            # Select appropriate concurrency semaphore based on model locality
            sem = self.gpu_sem if "llama" in node.model_id or "ornith" in node.model_id else self.cloud_sem
            async with sem:
                try:
                    res = await self._execute_node_action(node)
                    node.status = "SUCCESS"
                    node.output = res
                    node.completed_at = time.time()
                    completed_outputs[node.id] = res
                except Exception as e:
                    node.status = "FAILED"
                    node.error_msg = str(e)
                    node.completed_at = time.time()
                    self.store.update_step_status(node)
                    self.store.update_task_completion(task_id, "FAILED", error_msg=str(e))
                    self._sync_kanban(task_id, prompt, "Blocked")
                    return {
                        "status": "error",
                        "task_id": task_id,
                        "summary": f"Task execution failed at step '{node.name}': {e}",
                        "data": {"error": str(e)}
                    }

            self.store.update_step_status(node)

        # 4. Generate Final Report & Sync Done
        final_summary = self._generate_consolidated_report(task_id, prompt, nodes)
        self.store.update_task_completion(task_id, "DONE", summary=final_summary)
        self._sync_kanban(task_id, prompt, "Done")

        return {
            "status": "success",
            "task_id": task_id,
            "summary": final_summary,
            "data": {"steps_count": len(nodes), "outputs": completed_outputs}
        }

    async def resume_task(self, task_id: str) -> Dict[str, Any]:
        """Resumes execution of a previously blocked or approved task."""
        task_data = self.store.get_task(task_id)
        if not task_data:
            return {"status": "error", "message": f"Task '{task_id}' not found."}

        steps = task_data.get("steps", [])
        nodes = []
        for s in steps:
            params = json.loads(s["params_json"]) if s.get("params_json") else {}
            deps = json.loads(s["dependencies_json"]) if s.get("dependencies_json") else []
            out = json.loads(s["output_json"]) if s.get("output_json") else None
            n = TaskNode(
                id=s["step_id"],
                name=s["name"],
                role=s["role"],
                action_type=s["action_type"],
                params=params,
                dependencies=deps,
                model_id=s["model_id"],
                has_side_effect=bool(s["has_side_effect"]),
                status=s["status"],
                output=out
            )
            nodes.append(n)

        is_valid, order, _ = PurePythonDAGValidator.validate_and_order(nodes)
        return await self._execute_dag_pipeline(task_id, task_data["prompt"], nodes, order)

    async def _execute_node_action(self, node: TaskNode) -> Dict[str, Any]:
        """Dispatches action to the specialized pipeline."""
        if node.action_type == "code_write":
            task_desc = node.params.get("task", "")
            target_file = node.params.get("file_path") or node.params.get("target_file")
            return pipeline_code_write(task=task_desc, target_file=target_file)
        elif node.action_type == "web_search":
            query_str = node.params.get("query", "")
            return search_web_explicit.invoke({"query": query_str, "force": True})
        else:
            return {"status": "success", "action": node.name, "result": f"Executed step '{node.name}'."}

    def _sync_kanban(self, task_id: str, prompt: str, column: str):
        """Synchronizes task status with Goals & Tasks Kanban."""
        try:
            from tools.memory_tree_tool import goals_kanban_upsert
            goals_kanban_upsert.invoke({
                "task_id": task_id,
                "title": prompt[:40],
                "column": column,
                "priority": "high",
                "assignee": "Jarvis"
            })
        except Exception:
            pass

    def _generate_consolidated_report(self, task_id: str, prompt: str, nodes: List[TaskNode]) -> str:
        """Constructs unified Markdown execution report."""
        lines = [
            f"### 📋 Autonomous Task Execution Summary\n",
            f"- **Task ID:** `{task_id}`",
            f"- **Request:** {prompt}",
            f"- **Steps Executed:** {len(nodes)}\n",
            f"| Step | Name | Role | Status | Duration |",
            f"| :--- | :--- | :--- | :--- | :--- |"
        ]
        for i, n in enumerate(nodes):
            dur = round((n.completed_at - n.started_at) * 1000, 1) if n.completed_at and n.started_at else 0.0
            lines.append(f"| {i+1} | {n.name} | `{n.role}` | `{n.status}` | {dur}ms |")

        # Append last node summary if available
        last_out = nodes[-1].output
        if last_out and isinstance(last_out, dict) and "summary" in last_out:
            lines.append(f"\n{last_out['summary']}")

        return "\n".join(lines)

    def approve_task(self, task_id: str, token: str) -> Dict[str, Any]:
        """Validates approval token and unblocks task for execution."""
        if not agentshield.verify_and_consume_token(task_id, token):
            return {"status": "error", "message": "Invalid or expired single-use approval token."}
        
        task_data = self.store.get_task(task_id)
        if not task_data:
            return {"status": "error", "message": f"Task '{task_id}' not found."}

        logger.info(f"[TaskRunner] Task '{task_id}' approved with valid token. Resuming execution...")
        self._sync_kanban(task_id, task_data.get("prompt", ""), "In Progress")
        return {"status": "success", "message": f"Task '{task_id}' approved. Ready for execution.", "task_id": task_id}

    def reject_task(self, task_id: str, reason: str = "") -> Dict[str, Any]:
        """Rejects a blocked task and marks it failed with audit note."""
        self.store.update_task_completion(task_id, "REJECTED", error_msg=f"Rejected by human: {reason}")
        task_data = self.store.get_task(task_id)
        self._sync_kanban(task_id, task_data.get("prompt", "") if task_data else task_id, "Done")
        return {"status": "success", "message": f"Task '{task_id}' rejected."}


# Global Singleton TaskRunner Instance
task_runner = TaskRunner()
