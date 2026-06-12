"""
Task Graph Engine — Phase 2
Orchestrates the complete Phase 2 pipeline:

Plan (Phase 1 output)
  ↓
Task Decomposer     → atomic tasks
  ↓
Dependency Builder  → dependency graph
  ↓
Graph Validator     → validate (cycle detection, orphan check, etc.)
  ↓
Execution Planner   → execution waves
  ↓
Graph Storage       → persist to database
  ↓
Task Graph          ← complete output

NO EXECUTION. PLANNING ONLY.
"""

import uuid
import logging
from dataclasses import dataclass, field
from typing import Optional

from app.agent.task_decomposer import TaskDecomposer, AtomicTask
from app.agent.dependency_builder import DependencyBuilder, DependencyGraph
from app.agent.graph_validator import GraphValidator, GraphValidationResult
from app.agent.execution_planner import ExecutionPlanner, ExecutionPlan, ExecutionWave
from app.agent.graph_storage import GraphStorage
from app.agent.plan_storage import PlanStorage

logger = logging.getLogger(__name__)

MAX_REGENERATION_ATTEMPTS = 3


@dataclass
class TaskGraph:
    """Complete task graph with all metadata."""
    graph_id: str
    plan_id: str
    goal: str
    tasks: list[AtomicTask]
    dep_graph: DependencyGraph
    execution_plan: ExecutionPlan
    validation: GraphValidationResult
    provider_used: str = ""
    regeneration_count: int = 0

    def to_dict(self) -> dict:
        """Serialize to dict for API response."""
        return {
            "graph_id": self.graph_id,
            "plan_id": self.plan_id,
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks],
            "dependencies": [d.to_dict() for d in self.dep_graph.dependencies],
            "execution_plan": self.execution_plan.to_dict(),
            "validation": self.validation.to_dict(),
            "stats": {
                "total_tasks": len(self.tasks),
                "total_dependencies": len(self.dep_graph.dependencies),
                "total_waves": self.execution_plan.total_waves,
                "max_parallel": self.execution_plan.max_parallel,
                "blocking_tasks": len(self.dep_graph.blocking_task_ids),
                "parallel_tasks": sum(
                    1 for t in self.tasks if t.parallelizable
                ),
                "estimated_duration": self.execution_plan.estimated_duration,
            },
            "provider_used": self.provider_used,
            "regeneration_count": self.regeneration_count,
        }


@dataclass
class TaskGraphResult:
    """Result from the Task Graph Engine."""
    success: bool
    graph: Optional[TaskGraph] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "graph": self.graph.to_dict() if self.graph else None,
            "error": self.error,
        }


class TaskGraphEngine:
    """
    Orchestrates Phase 2: plan → task graph.

    Pipeline:
    1. Load plan from Phase 1 (by plan_id)
    2. Decompose plan steps into atomic tasks
    3. Build dependency graph
    4. Validate graph (with auto-fix for minor issues)
    5. Generate execution waves
    6. Persist to database
    7. Return TaskGraph

    No tasks are executed. Status is always PLANNED.
    """

    def __init__(self):
        self.decomposer = TaskDecomposer()
        self.dep_builder = DependencyBuilder()
        self.validator = GraphValidator()
        self.exec_planner = ExecutionPlanner()
        self.graph_storage = GraphStorage()
        self.plan_storage = PlanStorage()

    async def create_graph(
        self,
        plan_id: str,
        conn,
    ) -> TaskGraphResult:
        """
        Create a task graph from an existing plan.

        Args:
            plan_id: ID of Phase 1 plan to decompose
            conn: Database connection

        Returns:
            TaskGraphResult with complete task graph
        """
        logger.info(f"[Phase2] Creating task graph for plan_id={plan_id}")

        # Load plan from Phase 1
        plan = await self.plan_storage.get_plan(conn, plan_id)
        if not plan:
            return TaskGraphResult(
                success=False,
                error=f"Plan '{plan_id}' not found",
            )

        goal = plan.get("goal", "")
        steps = plan.get("steps", [])

        logger.info(f"[Phase2] Loaded plan: goal='{goal[:60]}', {len(steps)} steps")

        return await self._build_graph_with_retry(
            plan_id=plan_id,
            goal=goal,
            plan_steps=steps,
            conn=conn,
        )

    async def create_graph_from_plan_data(
        self,
        plan_id: str,
        goal: str,
        plan_steps: list[dict],
        conn,
    ) -> TaskGraphResult:
        """
        Create a task graph from inline plan data (for testing / direct creation).
        """
        logger.info(f"[Phase2] Creating task graph from inline data: goal='{goal[:60]}'")
        return await self._build_graph_with_retry(
            plan_id=plan_id,
            goal=goal,
            plan_steps=plan_steps,
            conn=conn,
        )

    async def _build_graph_with_retry(
        self,
        plan_id: str,
        goal: str,
        plan_steps: list[dict],
        conn,
        attempt: int = 0,
    ) -> TaskGraphResult:
        """Build graph with up to MAX_REGENERATION_ATTEMPTS on validation failure."""
        graph_id = str(uuid.uuid4())

        # Step 2: Decompose
        logger.info(f"[Phase2] Step 2: Decomposing plan steps (attempt {attempt+1})")
        tasks: list[AtomicTask] = await self.decomposer.decompose(goal, plan_steps)

        if not tasks:
            return TaskGraphResult(
                success=False,
                error="Task decomposition produced no tasks",
            )

        # Step 3: Build dependency graph
        logger.info(f"[Phase2] Step 3: Building dependency graph for {len(tasks)} tasks")
        dep_graph: DependencyGraph = self.dep_builder.build(tasks)

        # Step 4: Validate
        logger.info("[Phase2] Step 4: Validating graph")
        task_ids = {t.id for t in tasks}
        validation: GraphValidationResult = self.validator.validate(tasks, dep_graph)

        # Auto-fix minor issues
        if not validation.is_valid and not validation.should_regenerate:
            logger.info("[Phase2] Applying auto-fix for minor validation issues")
            tasks = self.validator.fix_minor_issues(tasks, task_ids)
            dep_graph = self.dep_builder.build(tasks)
            validation = self.validator.validate(tasks, dep_graph)

        # Retry on critical failures
        if not validation.is_valid and validation.should_regenerate and attempt < MAX_REGENERATION_ATTEMPTS:
            logger.warning(f"[Phase2] Graph invalid (attempt {attempt+1}), regenerating...")
            return await self._build_graph_with_retry(
                plan_id=plan_id,
                goal=goal,
                plan_steps=plan_steps,
                conn=conn,
                attempt=attempt + 1,
            )

        # Step 5: Generate execution waves
        logger.info("[Phase2] Step 5: Generating execution plan")
        execution_plan: ExecutionPlan = self.exec_planner.generate_execution_plan(
            tasks=tasks,
            prerequisites=dep_graph.prerequisites,
            blocking_task_ids=dep_graph.blocking_task_ids,
            graph_id=graph_id,
        )
        execution_plan.graph_id = graph_id

        # Build TaskGraph
        task_graph = TaskGraph(
            graph_id=graph_id,
            plan_id=plan_id,
            goal=goal,
            tasks=tasks,
            dep_graph=dep_graph,
            execution_plan=execution_plan,
            validation=validation,
            regeneration_count=attempt,
        )

        # Step 6: Persist to database
        logger.info("[Phase2] Step 6: Persisting task graph to database")
        try:
            await self.graph_storage.save_graph(
                conn=conn,
                graph_id=graph_id,
                plan_id=plan_id,
                goal=goal,
                validation=validation.to_dict(),
            )
            await self.graph_storage.save_tasks(
                conn=conn,
                graph_id=graph_id,
                tasks=[t.to_dict() for t in tasks],
            )
            await self.graph_storage.save_dependencies(
                conn=conn,
                graph_id=graph_id,
                dependencies=[d.to_dict() for d in dep_graph.dependencies],
            )
            await self.graph_storage.save_execution_waves(
                conn=conn,
                graph_id=graph_id,
                waves=[w.to_dict() for w in execution_plan.waves],
            )
            logger.info(f"[Phase2] Graph {graph_id} persisted successfully")
        except Exception as e:
            logger.error(f"[Phase2] Failed to persist graph: {e}")
            # Return graph even if storage failed

        logger.info(
            f"[Phase2] Task graph complete: {len(tasks)} tasks, "
            f"{len(dep_graph.dependencies)} deps, "
            f"{execution_plan.total_waves} waves"
        )

        return TaskGraphResult(success=True, graph=task_graph)

    async def get_graph(self, graph_id: str, conn) -> Optional[dict]:
        """Retrieve a stored task graph."""
        return await self.graph_storage.get_graph(conn, graph_id)

    async def list_graphs(self, conn, limit: int = 20, offset: int = 0) -> list[dict]:
        """List all task graphs."""
        return await self.graph_storage.list_graphs(conn, limit=limit, offset=offset)

    async def get_waves(self, graph_id: str, conn) -> list[dict]:
        """Get execution waves for a graph."""
        return await self.graph_storage.get_waves(conn, graph_id)
