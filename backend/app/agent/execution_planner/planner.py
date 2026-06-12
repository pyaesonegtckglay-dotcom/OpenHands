"""
Execution Planner — Phase 2
Generates the execution wave sequence for a validated task graph.

Execution Waves:
  Wave 1: Tasks with no prerequisites (can start immediately)
  Wave 2: Tasks whose prerequisites are all in Wave 1
  Wave 3: Tasks whose prerequisites are all in Wave 1+2
  ...etc.

This is PLANNING ONLY. No execution occurs.
Tasks within the same wave can run in parallel.
Tasks in later waves must wait for prior waves.
"""

import logging
from dataclasses import dataclass, field
from collections import defaultdict, deque

from app.agent.task_decomposer import AtomicTask

logger = logging.getLogger(__name__)


@dataclass
class ExecutionWave:
    """A single execution wave — tasks that can run simultaneously."""
    wave_number: int
    task_ids: list[str]
    task_titles: list[str]
    can_run_parallel: bool       # True if multiple tasks in this wave
    all_blocking: bool           # True if all tasks in this wave block the next

    def to_dict(self) -> dict:
        return {
            "wave_number": self.wave_number,
            "task_ids": self.task_ids,
            "task_titles": self.task_titles,
            "can_run_parallel": self.can_run_parallel,
            "all_blocking": self.all_blocking,
        }


@dataclass
class ExecutionPlan:
    """Complete execution plan with ordered waves."""
    graph_id: str
    waves: list[ExecutionWave]
    total_waves: int
    total_tasks: int
    max_parallel: int            # Max tasks that can run simultaneously
    estimated_duration: str      # Rough estimate

    def to_dict(self) -> dict:
        return {
            "graph_id": self.graph_id,
            "total_waves": self.total_waves,
            "total_tasks": self.total_tasks,
            "max_parallel": self.max_parallel,
            "estimated_duration": self.estimated_duration,
            "waves": [w.to_dict() for w in self.waves],
        }


class ExecutionPlanner:
    """
    Generates execution waves using topological sort (BFS-based Kahn's algorithm).

    Algorithm:
    1. Compute in-degree for each task
    2. Wave 1 = tasks with in-degree 0
    3. Remove Wave 1 tasks from graph
    4. Wave 2 = tasks that now have in-degree 0
    5. Repeat until all tasks are placed
    """

    def generate_execution_plan(
        self,
        tasks: list[AtomicTask],
        prerequisites: dict[str, list[str]],
        blocking_task_ids: set[str],
        graph_id: str = "",
    ) -> ExecutionPlan:
        """
        Generate wave-by-wave execution plan.

        Args:
            tasks: All atomic tasks
            prerequisites: task_id → [prerequisite task_ids]
            blocking_task_ids: set of blocking task IDs
            graph_id: ID of the parent task graph

        Returns:
            ExecutionPlan with ordered execution waves
        """
        logger.info(f"Generating execution plan for {len(tasks)} tasks")

        if not tasks:
            return ExecutionPlan(
                graph_id=graph_id,
                waves=[],
                total_waves=0,
                total_tasks=0,
                max_parallel=0,
                estimated_duration="0 minutes",
            )

        # Build adjacency for topological sort
        task_map = {t.id: t for t in tasks}
        task_ids = list(task_map.keys())

        in_degree: dict[str, int] = {tid: 0 for tid in task_ids}
        adj: dict[str, list[str]] = defaultdict(list)  # prereq → [dependents]

        for tid in task_ids:
            for prereq in prerequisites.get(tid, []):
                if prereq in task_map:
                    adj[prereq].append(tid)
                    in_degree[tid] += 1

        # BFS wave generation
        waves: list[ExecutionWave] = []
        wave_number = 1
        processed = set()

        # Initial wave: all tasks with in_degree=0
        current_wave_ids = [tid for tid in task_ids if in_degree[tid] == 0]

        while current_wave_ids:
            wave_tasks = [task_map[tid] for tid in current_wave_ids if tid in task_map]
            wave_task_titles = [t.title for t in wave_tasks]

            can_parallel = len(current_wave_ids) > 1
            all_blocking = all(tid in blocking_task_ids for tid in current_wave_ids)

            wave = ExecutionWave(
                wave_number=wave_number,
                task_ids=list(current_wave_ids),
                task_titles=wave_task_titles,
                can_run_parallel=can_parallel,
                all_blocking=all_blocking,
            )
            waves.append(wave)

            # Mark processed and find next wave
            for tid in current_wave_ids:
                processed.add(tid)

            next_wave_ids = []
            for tid in current_wave_ids:
                for dependent in adj.get(tid, []):
                    if dependent not in processed:
                        in_degree[dependent] -= 1
                        if in_degree[dependent] == 0:
                            if dependent not in next_wave_ids:
                                next_wave_ids.append(dependent)

            current_wave_ids = next_wave_ids
            wave_number += 1

        # Handle any remaining tasks (in case of disconnected subgraphs)
        remaining = [tid for tid in task_ids if tid not in processed]
        if remaining:
            wave_tasks = [task_map[tid] for tid in remaining if tid in task_map]
            waves.append(ExecutionWave(
                wave_number=wave_number,
                task_ids=remaining,
                task_titles=[t.title for t in wave_tasks],
                can_run_parallel=len(remaining) > 1,
                all_blocking=False,
            ))

        max_parallel = max((len(w.task_ids) for w in waves), default=1)
        estimated_duration = self._estimate_duration(tasks, waves)

        logger.info(f"Execution plan: {len(waves)} waves, max_parallel={max_parallel}")

        return ExecutionPlan(
            graph_id=graph_id,
            waves=waves,
            total_waves=len(waves),
            total_tasks=len(tasks),
            max_parallel=max_parallel,
            estimated_duration=estimated_duration,
        )

    def _estimate_duration(
        self,
        tasks: list[AtomicTask],
        waves: list[ExecutionWave],
    ) -> str:
        """Rough duration estimate based on task complexity."""
        task_map = {t.id: t for t in tasks}
        total_minutes = 0

        for wave in waves:
            # Wave duration = max task duration in wave (parallel execution)
            wave_max = 0
            for tid in wave.task_ids:
                task = task_map.get(tid)
                if task:
                    # Parse duration estimate
                    dur_str = task.estimated_duration.lower()
                    nums = [int(x) for x in dur_str.split() if x.isdigit()]
                    if nums:
                        wave_max = max(wave_max, max(nums))
                    else:
                        wave_max = max(wave_max, 15)
            total_minutes += wave_max

        if total_minutes < 60:
            return f"~{total_minutes} minutes"
        hours = total_minutes // 60
        mins = total_minutes % 60
        if mins:
            return f"~{hours}h {mins}m"
        return f"~{hours} hour{'s' if hours > 1 else ''}"
