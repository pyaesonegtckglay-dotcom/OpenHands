"""
Dependency Builder — Phase 2
Creates and validates dependency relationships between tasks.
Detects cycles (A→B→C→A forbidden).
Identifies parallel tasks and blocking tasks.

Rules:
- Task B depends on Task A: A must complete before B starts
- Parallel tasks: tasks with no dependency between them at the same level
- Blocking tasks: tasks that must complete before any dependent tasks run
"""

import logging
from dataclasses import dataclass, field
from collections import defaultdict, deque
from typing import Optional

from app.agent.task_decomposer import AtomicTask

logger = logging.getLogger(__name__)


@dataclass
class TaskDependency:
    """A directed dependency edge: source → target (target depends on source)."""
    id: str
    source_task_id: str   # task that must complete first
    target_task_id: str   # task that depends on source
    graph_id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_task_id": self.source_task_id,
            "target_task_id": self.target_task_id,
            "graph_id": self.graph_id,
        }


@dataclass
class DependencyGraph:
    """
    Dependency graph for a set of atomic tasks.
    Contains adjacency maps and parallel/blocking analysis.
    """
    tasks: list[AtomicTask]
    dependencies: list[TaskDependency]
    # task_id → list of task_ids that depend on it
    dependents: dict[str, list[str]] = field(default_factory=dict)
    # task_id → list of task_ids this task depends on
    prerequisites: dict[str, list[str]] = field(default_factory=dict)
    has_cycle: bool = False
    cycle_path: list[str] = field(default_factory=list)
    parallel_groups: list[list[str]] = field(default_factory=list)
    blocking_task_ids: set[str] = field(default_factory=set)
    orphan_task_ids: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "task_count": len(self.tasks),
            "dependency_count": len(self.dependencies),
            "has_cycle": self.has_cycle,
            "cycle_path": self.cycle_path,
            "parallel_groups": self.parallel_groups,
            "blocking_task_ids": list(self.blocking_task_ids),
            "orphan_task_ids": list(self.orphan_task_ids),
        }


class DependencyBuilder:
    """
    Builds and analyzes the dependency graph for atomic tasks.

    Steps:
    1. Build adjacency maps from task.dependencies
    2. Detect cycles using DFS
    3. Identify parallel tasks (tasks with no dependency path between them)
    4. Mark blocking tasks
    5. Find orphaned tasks
    """

    def build(self, tasks: list[AtomicTask]) -> DependencyGraph:
        """Build dependency graph from list of atomic tasks."""
        logger.info(f"Building dependency graph for {len(tasks)} tasks")

        if not tasks:
            return DependencyGraph(tasks=[], dependencies=[])

        task_ids = {t.id for t in tasks}

        # Build prerequisite and dependent maps
        prerequisites: dict[str, list[str]] = defaultdict(list)
        dependents: dict[str, list[str]] = defaultdict(list)
        dependencies: list[TaskDependency] = []

        dep_counter = 1
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    logger.warning(f"Task {task.id} references unknown dependency {dep_id} — skipping")
                    continue
                prerequisites[task.id].append(dep_id)
                dependents[dep_id].append(task.id)
                dependencies.append(TaskDependency(
                    id=f"dep_{dep_counter}",
                    source_task_id=dep_id,
                    target_task_id=task.id,
                ))
                dep_counter += 1

        graph = DependencyGraph(
            tasks=tasks,
            dependencies=dependencies,
            dependents=dict(dependents),
            prerequisites=dict(prerequisites),
        )

        # Cycle detection
        has_cycle, cycle_path = self._detect_cycle(tasks, prerequisites)
        graph.has_cycle = has_cycle
        graph.cycle_path = cycle_path

        # Orphan detection (tasks not connected to root)
        graph.orphan_task_ids = self._find_orphans(tasks, prerequisites, dependents)

        # Blocking tasks detection
        graph.blocking_task_ids = self._find_blocking_tasks(tasks, dependents)

        # Parallel groups
        graph.parallel_groups = self._find_parallel_groups(tasks, prerequisites)

        # Update task.parallelizable and task.is_blocking
        parallel_flat = {tid for group in graph.parallel_groups for tid in group if len(group) > 1}
        for task in tasks:
            task.parallelizable = task.id in parallel_flat
            task.is_blocking = task.id in graph.blocking_task_ids

        logger.info(
            f"Dependency graph built: {len(dependencies)} deps, "
            f"cycle={has_cycle}, blocking={len(graph.blocking_task_ids)}, "
            f"orphans={len(graph.orphan_task_ids)}"
        )
        return graph

    def _detect_cycle(
        self,
        tasks: list[AtomicTask],
        prerequisites: dict[str, list[str]],
    ) -> tuple[bool, list[str]]:
        """
        Detect cycles using DFS (Kahn's algorithm + path tracking).
        Returns (has_cycle, cycle_path).
        """
        # Build adjacency: prerequisite → task (reverse of what we store)
        # We want to detect: A→B→C→A where → means "must come before"
        # Store graph as: node → nodes it must come before (dependents)
        task_ids = [t.id for t in tasks]
        in_degree: dict[str, int] = {tid: 0 for tid in task_ids}
        adj: dict[str, list[str]] = defaultdict(list)

        for tid in task_ids:
            for prereq in prerequisites.get(tid, []):
                adj[prereq].append(tid)
                in_degree[tid] += 1

        # Kahn's BFS topological sort
        queue = deque([tid for tid in task_ids if in_degree[tid] == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count == len(task_ids):
            return False, []

        # Cycle exists — find one cycle path using DFS
        cycle_path = self._find_cycle_path(task_ids, prerequisites)
        return True, cycle_path

    def _find_cycle_path(
        self,
        task_ids: list[str],
        prerequisites: dict[str, list[str]],
    ) -> list[str]:
        """DFS to find a cycle path."""
        visited = set()
        path = []
        path_set = set()

        # Build forward graph (dep → node that depends on it)
        forward: dict[str, list[str]] = defaultdict(list)
        for tid in task_ids:
            for pre in prerequisites.get(tid, []):
                forward[pre].append(tid)

        def dfs(node: str) -> Optional[list[str]]:
            if node in path_set:
                idx = path.index(node)
                return path[idx:] + [node]
            if node in visited:
                return None
            visited.add(node)
            path.append(node)
            path_set.add(node)
            for neighbor in forward.get(node, []):
                result = dfs(neighbor)
                if result:
                    return result
            path.pop()
            path_set.discard(node)
            return None

        for tid in task_ids:
            if tid not in visited:
                result = dfs(tid)
                if result:
                    return result
        return []

    def _find_orphans(
        self,
        tasks: list[AtomicTask],
        prerequisites: dict[str, list[str]],
        dependents: dict[str, list[str]],
    ) -> set[str]:
        """
        Find tasks not connected to any other task (isolated nodes).
        Root tasks (no prerequisites) are NOT orphans if other tasks depend on them.
        """
        if len(tasks) <= 1:
            return set()

        orphans = set()
        for task in tasks:
            has_deps = bool(prerequisites.get(task.id))
            has_dependents = bool(dependents.get(task.id))
            # Orphan: no prerequisites AND no dependents AND more than 1 task total
            if not has_deps and not has_dependents:
                orphans.add(task.id)

        return orphans

    def _find_blocking_tasks(
        self,
        tasks: list[AtomicTask],
        dependents: dict[str, list[str]],
    ) -> set[str]:
        """
        A task is blocking if other tasks depend on it.
        Specifically: tasks with 2+ dependents or tasks that other tasks explicitly depend on.
        """
        blocking = set()
        for task in tasks:
            deps = dependents.get(task.id, [])
            if deps:  # Any task that others depend on is blocking
                blocking.add(task.id)
        return blocking

    def _find_parallel_groups(
        self,
        tasks: list[AtomicTask],
        prerequisites: dict[str, list[str]],
    ) -> list[list[str]]:
        """
        Find groups of tasks that can execute in parallel.
        Tasks can run in parallel if they share the same set of prerequisites
        and don't depend on each other.
        """
        # Group by their prerequisite set
        prereq_groups: dict[str, list[str]] = defaultdict(list)
        for task in tasks:
            prereqs = frozenset(prerequisites.get(task.id, []))
            key = ",".join(sorted(prereqs))
            prereq_groups[key].append(task.id)

        parallel_groups = []
        for key, group in prereq_groups.items():
            if len(group) >= 2:
                # These tasks share identical prerequisites → can run in parallel
                parallel_groups.append(group)
            else:
                parallel_groups.append(group)

        return parallel_groups
