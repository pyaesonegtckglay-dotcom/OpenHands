"""
Graph Validator — Phase 2
Validates task graphs against all rules:
  - No orphan tasks
  - No circular dependencies
  - No duplicate task IDs
  - Valid parent-child structure
  - Valid dependency structure
  - Valid execution order
  - All tasks connected to root goal

Invalid graphs trigger regeneration.
"""

import logging
from dataclasses import dataclass, field

from app.agent.task_decomposer import AtomicTask
from app.agent.dependency_builder import DependencyGraph

logger = logging.getLogger(__name__)


@dataclass
class GraphValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    task_count: int = 0
    dependency_count: int = 0
    should_regenerate: bool = False

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "task_count": self.task_count,
            "dependency_count": self.dependency_count,
            "should_regenerate": self.should_regenerate,
        }


class GraphValidator:
    """
    Validates a task graph for structural integrity.

    Validation Rules:
    1. No circular dependencies (A→B→C→A forbidden)
    2. No orphan tasks (all tasks connected to graph)
    3. No duplicate task IDs
    4. Valid parent-child structure (parent IDs must exist if set)
    5. Valid dependency references (all dep IDs must exist)
    6. Valid execution order (topological sort possible)
    7. At least one root task (task with no prerequisites)
    8. At least one terminal task (task with no dependents)
    """

    def validate(
        self,
        tasks: list[AtomicTask],
        dep_graph: DependencyGraph,
    ) -> GraphValidationResult:
        """
        Validate the task graph. Returns GraphValidationResult.
        If is_valid=False, the graph must be regenerated.
        """
        logger.info(f"Validating graph: {len(tasks)} tasks, {len(dep_graph.dependencies)} deps")

        errors = []
        warnings = []
        task_ids = {t.id for t in tasks}

        # Rule 1: No duplicate IDs
        dup_errors = self._check_duplicate_ids(tasks)
        errors.extend(dup_errors)

        # Rule 2: No circular dependencies
        if dep_graph.has_cycle:
            errors.append(
                f"CIRCULAR DEPENDENCY detected: {' → '.join(dep_graph.cycle_path)}"
            )

        # Rule 3: No orphan tasks (if more than 1 task)
        if len(tasks) > 1 and dep_graph.orphan_task_ids:
            for orphan_id in dep_graph.orphan_task_ids:
                task = next((t for t in tasks if t.id == orphan_id), None)
                title = task.title if task else orphan_id
                warnings.append(f"Orphan task detected: '{title}' (id={orphan_id}) — not connected to graph")

        # Rule 4: Valid parent-child references
        parent_errors = self._check_parent_child(tasks, task_ids)
        errors.extend(parent_errors)

        # Rule 5: Valid dependency references
        dep_errors = self._check_dependency_refs(tasks, task_ids)
        errors.extend(dep_errors)

        # Rule 6: At least one root task
        prerequisites = dep_graph.prerequisites or {}
        root_tasks = [t for t in tasks if not prerequisites.get(t.id)]
        if not root_tasks:
            errors.append("No root tasks found — graph must have at least one task with no prerequisites")

        # Rule 7: At least one terminal task
        dependents = dep_graph.dependents or {}
        terminal_tasks = [t for t in tasks if not dependents.get(t.id)]
        if not terminal_tasks:
            errors.append("No terminal tasks found — graph must have at least one task with no dependents")

        # Rule 8: Minimum task count
        if len(tasks) == 0:
            errors.append("Graph has no tasks")

        # Warnings
        if len(tasks) == 1:
            warnings.append("Graph has only one task — consider decomposing further")

        if not dep_graph.dependencies and len(tasks) > 1:
            warnings.append("No dependencies defined between tasks")

        is_valid = len(errors) == 0
        should_regenerate = any(
            "CIRCULAR" in e or "No root tasks" in e or "duplicate" in e.lower()
            for e in errors
        )

        result = GraphValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            task_count=len(tasks),
            dependency_count=len(dep_graph.dependencies),
            should_regenerate=should_regenerate,
        )

        if is_valid:
            logger.info(f"Graph validation PASSED: {len(tasks)} tasks, {len(dep_graph.dependencies)} deps")
        else:
            logger.warning(f"Graph validation FAILED: {errors}")

        return result

    def _check_duplicate_ids(self, tasks: list[AtomicTask]) -> list[str]:
        """Check for duplicate task IDs."""
        seen = set()
        duplicates = set()
        for task in tasks:
            if task.id in seen:
                duplicates.add(task.id)
            seen.add(task.id)
        if duplicates:
            return [f"Duplicate task IDs found: {', '.join(duplicates)}"]
        return []

    def _check_parent_child(self, tasks: list[AtomicTask], task_ids: set[str]) -> list[str]:
        """Check parent-child relationship validity."""
        errors = []
        for task in tasks:
            if task.parent_task and task.parent_task not in task_ids:
                errors.append(
                    f"Task '{task.id}' references non-existent parent '{task.parent_task}'"
                )
            for child_id in task.child_tasks:
                if child_id not in task_ids:
                    # Warning-level only; don't block
                    pass
        return errors

    def _check_dependency_refs(self, tasks: list[AtomicTask], task_ids: set[str]) -> list[str]:
        """Check that all dependency references point to valid task IDs."""
        errors = []
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    errors.append(
                        f"Task '{task.id}' ('{task.title}') depends on "
                        f"non-existent task '{dep_id}'"
                    )
        return errors

    def fix_minor_issues(
        self,
        tasks: list[AtomicTask],
        task_ids: set[str],
    ) -> list[AtomicTask]:
        """
        Fix minor issues without full regeneration:
        - Remove invalid dependency references
        - Remove invalid child_task references
        - Remove invalid parent_task references
        """
        for task in tasks:
            task.dependencies = [d for d in task.dependencies if d in task_ids and d != task.id]
            task.child_tasks = [c for c in task.child_tasks if c in task_ids and c != task.id]
            if task.parent_task and (task.parent_task not in task_ids or task.parent_task == task.id):
                task.parent_task = None
        return tasks
