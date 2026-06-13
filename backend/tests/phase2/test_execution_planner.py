"""
Phase 2 Tests: Execution Planner
Tests execution wave generation.
"""
import pytest
from app.agent.execution_planner import ExecutionPlanner
from app.agent.task_decomposer import AtomicTask, TaskStatus, TaskComplexity


def make_task(id: str, deps: list[str] = None, duration: str = "10 min") -> AtomicTask:
    return AtomicTask(
        id=id,
        title=f"Task {id}",
        description="",
        expected_output="",
        estimated_complexity=TaskComplexity.MEDIUM,
        estimated_duration=duration,
        parent_task=None,
        child_tasks=[],
        dependencies=deps or [],
        status=TaskStatus.PLANNED,
        order=0,
    )


class TestExecutionPlanner:
    def setup_method(self):
        self.planner = ExecutionPlanner()

    def _build_prereqs(self, tasks: list[AtomicTask]) -> dict:
        return {t.id: t.dependencies for t in tasks}

    def test_single_wave_no_deps(self):
        """All tasks with no dependencies → single wave."""
        tasks = [make_task("t1"), make_task("t2"), make_task("t3")]
        prereqs = self._build_prereqs(tasks)
        plan = self.planner.generate_execution_plan(tasks, prereqs, set())
        assert plan.total_waves == 1
        assert set(plan.waves[0].task_ids) == {"t1", "t2", "t3"}
        assert plan.waves[0].can_run_parallel is True

    def test_linear_chain_produces_sequential_waves(self):
        """t1 → t2 → t3 → 3 waves."""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
            make_task("t3", deps=["t2"]),
        ]
        prereqs = self._build_prereqs(tasks)
        plan = self.planner.generate_execution_plan(tasks, prereqs, set())
        assert plan.total_waves == 3
        assert plan.waves[0].task_ids == ["t1"]
        assert plan.waves[1].task_ids == ["t2"]
        assert plan.waves[2].task_ids == ["t3"]
        assert plan.max_parallel == 1

    def test_diamond_pattern(self):
        """t1 → {t2, t3} → t4: 3 waves, wave 2 has 2 parallel tasks."""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
            make_task("t3", deps=["t1"]),
            make_task("t4", deps=["t2", "t3"]),
        ]
        prereqs = self._build_prereqs(tasks)
        plan = self.planner.generate_execution_plan(tasks, prereqs, set())
        assert plan.total_waves == 3
        wave_2 = plan.waves[1]
        assert set(wave_2.task_ids) == {"t2", "t3"}
        assert wave_2.can_run_parallel is True
        assert plan.max_parallel == 2

    def test_all_tasks_placed(self):
        """All tasks must appear in exactly one wave."""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
            make_task("t3", deps=["t1"]),
            make_task("t4", deps=["t2"]),
            make_task("t5", deps=["t3"]),
        ]
        prereqs = self._build_prereqs(tasks)
        plan = self.planner.generate_execution_plan(tasks, prereqs, set())
        all_placed = set()
        for wave in plan.waves:
            all_placed.update(wave.task_ids)
        assert all_placed == {"t1", "t2", "t3", "t4", "t5"}

    def test_empty_tasks_returns_empty_plan(self):
        plan = self.planner.generate_execution_plan([], {}, set())
        assert plan.total_waves == 0
        assert plan.waves == []

    def test_single_task_single_wave(self):
        tasks = [make_task("t1")]
        plan = self.planner.generate_execution_plan(tasks, {"t1": []}, set())
        assert plan.total_waves == 1
        assert plan.waves[0].task_ids == ["t1"]
        assert plan.waves[0].can_run_parallel is False

    def test_blocking_tasks_marked_in_wave(self):
        """Waves with blocking tasks should have all_blocking=True."""
        tasks = [
            make_task("t1"),
            make_task("t2", deps=["t1"]),
        ]
        prereqs = self._build_prereqs(tasks)
        blocking_ids = {"t1"}  # t1 blocks t2
        plan = self.planner.generate_execution_plan(tasks, prereqs, blocking_ids)
        assert plan.waves[0].all_blocking is True

    def test_plan_to_dict(self):
        tasks = [make_task("t1"), make_task("t2", deps=["t1"])]
        prereqs = self._build_prereqs(tasks)
        plan = self.planner.generate_execution_plan(tasks, prereqs, set(), graph_id="test-graph")
        d = plan.to_dict()
        assert d["graph_id"] == "test-graph"
        assert "total_waves" in d
        assert "waves" in d
        assert "estimated_duration" in d
        assert len(d["waves"]) == 2

    def test_wave_to_dict(self):
        tasks = [make_task("t1")]
        plan = self.planner.generate_execution_plan(tasks, {"t1": []}, set())
        wave_d = plan.waves[0].to_dict()
        assert "wave_number" in wave_d
        assert "task_ids" in wave_d
        assert "can_run_parallel" in wave_d

    def test_duration_estimate_minutes(self):
        tasks = [make_task("t1", duration="10 min"), make_task("t2", duration="20 min")]
        plan = self.planner.generate_execution_plan(tasks, {"t1": [], "t2": []}, set())
        # Both in same wave, max is 20 min
        assert "20" in plan.estimated_duration or "minute" in plan.estimated_duration
