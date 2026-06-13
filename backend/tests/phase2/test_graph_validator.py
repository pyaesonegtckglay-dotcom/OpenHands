"""
Phase 2 Tests: Graph Validator
"""
import pytest
from app.agent.graph_validator import GraphValidator
from app.agent.dependency_builder import DependencyBuilder, DependencyGraph
from app.agent.task_decomposer import AtomicTask, TaskStatus, TaskComplexity


def make_task(id: str, deps: list[str] = None) -> AtomicTask:
    return AtomicTask(
        id=id,
        title=f"Task {id}",
        description=f"Description for {id}",
        expected_output=f"Output of {id}",
        estimated_complexity=TaskComplexity.MEDIUM,
        estimated_duration="10 min",
        parent_task=None,
        child_tasks=[],
        dependencies=deps or [],
        status=TaskStatus.PLANNED,
        order=0,
    )


class TestGraphValidator:
    def setup_method(self):
        self.validator = GraphValidator()
        self.builder = DependencyBuilder()

    def test_valid_simple_graph(self):
        tasks = [make_task("t1"), make_task("t2", deps=["t1"])]
        graph = self.builder.build(tasks)
        result = self.validator.validate(tasks, graph)
        assert result.is_valid
        assert result.errors == []

    def test_valid_complex_graph(self):
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
            make_task("t3", deps=["t1"]),
            make_task("t4", deps=["t2", "t3"]),
        ]
        graph = self.builder.build(tasks)
        result = self.validator.validate(tasks, graph)
        assert result.is_valid

    def test_cycle_fails_validation(self):
        tasks = [
            make_task("t1", deps=["t2"]),
            make_task("t2", deps=["t1"]),
        ]
        graph = self.builder.build(tasks)
        result = self.validator.validate(tasks, graph)
        assert not result.is_valid
        assert any("CIRCULAR" in e for e in result.errors)
        assert result.should_regenerate

    def test_duplicate_ids_fail(self):
        tasks = [make_task("t1"), make_task("t1")]  # duplicate ID
        graph = DependencyGraph(tasks=tasks, dependencies=[])
        result = self.validator.validate(tasks, graph)
        assert not result.is_valid
        assert any("duplicate" in e.lower() for e in result.errors)

    def test_invalid_dependency_ref_fails(self):
        task = make_task("t1", deps=["NONEXISTENT"])
        tasks = [task]
        graph = DependencyGraph(tasks=tasks, dependencies=[])
        result = self.validator.validate(tasks, graph)
        assert not result.is_valid
        assert any("non-existent" in e.lower() or "nonexistent" in e.lower() for e in result.errors)

    def test_empty_graph_fails(self):
        graph = DependencyGraph(tasks=[], dependencies=[])
        result = self.validator.validate([], graph)
        assert not result.is_valid
        assert any("no tasks" in e.lower() for e in result.errors)

    def test_single_task_valid(self):
        tasks = [make_task("t1")]
        graph = self.builder.build(tasks)
        result = self.validator.validate(tasks, graph)
        assert result.is_valid
        # May have warnings
        assert any("one task" in w.lower() for w in result.warnings)

    def test_orphan_generates_warning(self):
        tasks = [make_task("t1"), make_task("t2", deps=["t1"]), make_task("t3")]
        graph = self.builder.build(tasks)
        result = self.validator.validate(tasks, graph)
        # Orphan t3 should generate a warning (not an error by default)
        assert any("orphan" in w.lower() for w in result.warnings)

    def test_task_count_in_result(self):
        tasks = [make_task("t1"), make_task("t2", deps=["t1"])]
        graph = self.builder.build(tasks)
        result = self.validator.validate(tasks, graph)
        assert result.task_count == 2

    def test_dependency_count_in_result(self):
        tasks = [make_task("t1"), make_task("t2", deps=["t1"])]
        graph = self.builder.build(tasks)
        result = self.validator.validate(tasks, graph)
        assert result.dependency_count == 1

    def test_to_dict(self):
        tasks = [make_task("t1"), make_task("t2", deps=["t1"])]
        graph = self.builder.build(tasks)
        result = self.validator.validate(tasks, graph)
        d = result.to_dict()
        assert "is_valid" in d
        assert "errors" in d
        assert "warnings" in d
        assert "task_count" in d
        assert "dependency_count" in d

    def test_fix_minor_issues(self):
        task = AtomicTask(
            id="t1",
            title="Task",
            description="",
            expected_output="",
            estimated_complexity=TaskComplexity.MEDIUM,
            estimated_duration="10 min",
            parent_task="INVALID_PARENT",
            child_tasks=["INVALID_CHILD"],
            dependencies=["INVALID_DEP"],
        )
        fixed = self.validator.fix_minor_issues([task], {"t1"})
        assert fixed[0].parent_task is None
        assert fixed[0].child_tasks == []
        assert fixed[0].dependencies == []
