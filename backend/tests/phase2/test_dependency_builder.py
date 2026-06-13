"""
Phase 2 Tests: Dependency Builder
Tests cycle detection, parallel group detection, blocking tasks, orphan detection.
"""
import pytest
from app.agent.dependency_builder import DependencyBuilder
from app.agent.task_decomposer import AtomicTask, TaskStatus, TaskComplexity


def make_task(id: str, deps: list[str] = None, **kwargs) -> AtomicTask:
    return AtomicTask(
        id=id,
        title=f"Task {id}",
        description="",
        expected_output="",
        estimated_complexity=TaskComplexity.MEDIUM,
        estimated_duration="10 min",
        parent_task=None,
        child_tasks=[],
        dependencies=deps or [],
        status=TaskStatus.PLANNED,
        order=0,
        parallelizable=False,
        is_blocking=False,
    )


class TestDependencyBuilder:
    def setup_method(self):
        self.builder = DependencyBuilder()

    def test_no_dependencies(self):
        tasks = [make_task("t1"), make_task("t2"), make_task("t3")]
        graph = self.builder.build(tasks)
        assert not graph.has_cycle
        assert len(graph.dependencies) == 0

    def test_linear_chain(self):
        """t1 → t2 → t3 (no cycle)"""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
            make_task("t3", deps=["t2"]),
        ]
        graph = self.builder.build(tasks)
        assert not graph.has_cycle
        assert len(graph.dependencies) == 2

    def test_cycle_detection_simple(self):
        """t1 → t2 → t1 (cycle!)"""
        tasks = [
            make_task("t1", deps=["t2"]),
            make_task("t2", deps=["t1"]),
        ]
        graph = self.builder.build(tasks)
        assert graph.has_cycle
        assert len(graph.cycle_path) >= 2

    def test_cycle_detection_long(self):
        """t1 → t2 → t3 → t1 (3-node cycle)"""
        tasks = [
            make_task("t1", deps=["t3"]),
            make_task("t2", deps=["t1"]),
            make_task("t3", deps=["t2"]),
        ]
        graph = self.builder.build(tasks)
        assert graph.has_cycle

    def test_no_cycle_with_diamond(self):
        """Diamond: t1 → t2, t1 → t3, t2 → t4, t3 → t4 (not a cycle)"""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
            make_task("t3", deps=["t1"]),
            make_task("t4", deps=["t2", "t3"]),
        ]
        graph = self.builder.build(tasks)
        assert not graph.has_cycle
        assert len(graph.dependencies) == 4

    def test_blocking_task_detection(self):
        """t1 is blocking because t2 and t3 both depend on it."""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
            make_task("t3", deps=["t1"]),
        ]
        graph = self.builder.build(tasks)
        assert "t1" in graph.blocking_task_ids

    def test_non_blocking_terminal(self):
        """t3 is terminal (nothing depends on it) → not blocking."""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
            make_task("t3", deps=["t2"]),
        ]
        graph = self.builder.build(tasks)
        assert "t3" not in graph.blocking_task_ids
        assert "t1" in graph.blocking_task_ids
        assert "t2" in graph.blocking_task_ids

    def test_parallel_group_detection(self):
        """t2 and t3 both only depend on t1 → can run in parallel."""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
            make_task("t3", deps=["t1"]),
        ]
        graph = self.builder.build(tasks)
        # Find the parallel group containing t2 and t3
        parallel_with_both = [
            group for group in graph.parallel_groups
            if "t2" in group and "t3" in group
        ]
        assert len(parallel_with_both) == 1

    def test_orphan_detection(self):
        """t3 has no deps and nothing depends on it → orphan."""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
            make_task("t3"),  # isolated orphan
        ]
        # t1 is NOT orphan: t2 depends on it
        # t2 is NOT orphan: it has deps
        # t3 IS orphan: no deps, nothing depends on it
        graph = self.builder.build(tasks)
        assert "t3" in graph.orphan_task_ids
        assert "t1" not in graph.orphan_task_ids

    def test_single_task_no_orphan(self):
        """Single task graph — should not report orphans."""
        tasks = [make_task("t1")]
        graph = self.builder.build(tasks)
        assert len(graph.orphan_task_ids) == 0

    def test_skips_unknown_dependency(self):
        """Dependency to non-existent task should be skipped gracefully."""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1", "NONEXISTENT"]),
        ]
        graph = self.builder.build(tasks)
        # Should only create dependency for t1 → t2
        assert len(graph.dependencies) == 1
        assert not graph.has_cycle

    def test_empty_task_list(self):
        graph = self.builder.build([])
        assert graph.tasks == []
        assert graph.dependencies == []
        assert not graph.has_cycle

    def test_dependency_to_dict(self):
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
        ]
        graph = self.builder.build(tasks)
        assert len(graph.dependencies) == 1
        d = graph.dependencies[0].to_dict()
        assert d["source_task_id"] == "t1"
        assert d["target_task_id"] == "t2"
