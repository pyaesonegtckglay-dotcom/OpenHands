"""
Phase 3 Tests: Execution Scheduler
Tests wave-based parallel execution, dependency tracking, cancellation.
Uses real calculator tool (fast, no network) for integration-style tests.
"""
import asyncio
import pytest
from app.agent.execution_scheduler.scheduler import (
    ExecutionScheduler,
    ScheduledTask,
    TaskState,
)


def make_task(
    id: str,
    wave: int = 0,
    tool_id: str = "calculator",
    params: dict = None,
    deps: list = None,
) -> ScheduledTask:
    return ScheduledTask(
        id=id,
        title=f"Task {id}",
        description=f"Description for {id}",
        expected_output="Some output",
        tool_id=tool_id,
        tool_params=params or {"expression": "1 + 1"},
        wave=wave,
        dependencies=deps or [],
    )


class TestExecutionScheduler:
    def setup_method(self):
        # Ensure calculator tool is registered
        import app.agent.tool_registry.tools  # noqa: F401
        self.scheduler = ExecutionScheduler()

    def test_single_task_executes(self):
        """A single calculator task should complete."""
        task = make_task("t1", wave=0, params={"expression": "2 + 2"})
        result = asyncio.run(self.scheduler.execute_graph(
            execution_id="exec_001",
            tasks_by_wave={0: [task]},
            max_parallel=1,
        ))
        assert "t1" in result
        assert result["t1"].state == TaskState.COMPLETED

    def test_multiple_tasks_in_wave(self):
        """Multiple tasks in same wave should all complete."""
        tasks = [
            make_task(f"t{i}", wave=0, params={"expression": f"{i} + {i}"})
            for i in range(1, 4)
        ]
        result = asyncio.run(self.scheduler.execute_graph(
            execution_id="exec_002",
            tasks_by_wave={0: tasks},
            max_parallel=3,
        ))
        for i in range(1, 4):
            assert result[f"t{i}"].state == TaskState.COMPLETED

    def test_multiple_waves_execute(self):
        """Tasks in wave 0 and wave 1 should both complete."""
        tasks_by_wave = {
            0: [make_task("w0_t1", wave=0, params={"expression": "10 + 5"})],
            1: [make_task("w1_t1", wave=1, params={"expression": "20 + 5"})],
        }
        result = asyncio.run(self.scheduler.execute_graph(
            execution_id="exec_003",
            tasks_by_wave=tasks_by_wave,
            max_parallel=2,
        ))
        assert result["w0_t1"].state == TaskState.COMPLETED
        assert result["w1_t1"].state == TaskState.COMPLETED

    def test_failed_tool_marks_task_failed(self):
        """Unknown tool should mark task as FAILED."""
        task = make_task("fail_t", wave=0, tool_id="nonexistent_tool_xyz")
        result = asyncio.run(self.scheduler.execute_graph(
            execution_id="exec_004",
            tasks_by_wave={0: [task]},
            max_parallel=1,
        ))
        assert "fail_t" in result
        assert result["fail_t"].state == TaskState.FAILED

    def test_cancellation_before_execution(self):
        """Pre-cancelled event should prevent task execution."""
        cancel_event = asyncio.Event()
        cancel_event.set()
        self.scheduler.cancel_event = cancel_event

        task = make_task("c1", wave=0)
        result = asyncio.run(self.scheduler.execute_graph(
            execution_id="exec_005",
            tasks_by_wave={0: [task]},
            max_parallel=1,
        ))
        assert isinstance(result, dict)
        # Task should be cancelled or remain in planned state (not completed)
        if "c1" in result:
            assert result["c1"].state in (TaskState.CANCELLED, TaskState.PLANNED)

    def test_empty_task_graph(self):
        """Empty task graph returns empty dict."""
        result = asyncio.run(self.scheduler.execute_graph(
            execution_id="exec_006",
            tasks_by_wave={},
            max_parallel=4,
        ))
        assert result == {}

    def test_get_stats_after_execution(self):
        """Stats correctly count completed tasks."""
        tasks_by_wave = {
            0: [
                make_task("s1", wave=0, params={"expression": "1+1"}),
                make_task("s2", wave=0, params={"expression": "2+2"}),
            ]
        }
        asyncio.run(self.scheduler.execute_graph(
            execution_id="exec_007",
            tasks_by_wave=tasks_by_wave,
            max_parallel=2,
        ))
        stats = self.scheduler.get_stats()
        assert "completed" in stats
        assert "failed" in stats
        assert "total" in stats
        assert stats["total"] == 2
        assert stats["completed"] == 2

    def test_event_callback_called(self):
        """Event callback fires during execution."""
        events_received = []

        async def callback(event_type: str, data: dict) -> None:
            events_received.append(event_type)

        scheduler = ExecutionScheduler(event_callback=callback)
        asyncio.run(scheduler.execute_graph(
            execution_id="exec_008",
            tasks_by_wave={0: [make_task("cb1", wave=0, params={"expression": "5*5"})]},
            max_parallel=1,
        ))
        assert len(events_received) > 0
        assert any("task" in e for e in events_received)

    def test_task_result_stored(self):
        """Completed task should have a result."""
        task = make_task("result_t", wave=0, params={"expression": "99"})
        result = asyncio.run(self.scheduler.execute_graph(
            execution_id="exec_009",
            tasks_by_wave={0: [task]},
            max_parallel=1,
        ))
        assert result["result_t"].result is not None

    def test_failed_task_has_error(self):
        """Failed task should have error message."""
        task = make_task("err_t", wave=0, tool_id="nonexistent_xyz")
        result = asyncio.run(self.scheduler.execute_graph(
            execution_id="exec_010",
            tasks_by_wave={0: [task]},
            max_parallel=1,
        ))
        assert result["err_t"].error is not None


class TestScheduledTask:
    def test_task_creation(self):
        task = make_task("test")
        assert task.id == "test"
        assert task.state == TaskState.PLANNED
        assert task.result is None
        assert task.error is None

    def test_to_dict(self):
        task = make_task("dict_task")
        d = task.to_dict()
        assert d["id"] == "dict_task"
        assert "state" in d
        assert "tool_id" in d
        assert "wave" in d
        assert "dependencies" in d

    def test_duration_ms_unstarted(self):
        task = make_task("unstarted")
        assert task.duration_ms == 0

    def test_task_state_values(self):
        states = [s.value for s in TaskState]
        assert "PLANNED" in states
        assert "RUNNING" in states
        assert "COMPLETED" in states
        assert "FAILED" in states
        assert "CANCELLED" in states

    def test_task_wave_set(self):
        task = make_task("wave_task", wave=2)
        assert task.wave == 2

    def test_task_tool_id_set(self):
        task = make_task("tool_task", tool_id="web_search")
        assert task.tool_id == "web_search"
