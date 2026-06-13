"""
Phase 3 Tests: Report Generator
Tests report generation from completed tasks, markdown formatting, statistics.
"""
import pytest
import time
from app.agent.report_generator.generator import ReportGenerator, ExecutionReport
from app.agent.execution_scheduler.scheduler import ScheduledTask, TaskState


def make_completed_task(
    id: str,
    title: str,
    tool_id: str = "calculator",
    state: TaskState = TaskState.COMPLETED,
    result: dict = None,
    error: str = None,
    execution_time_ms: int = 100,
) -> ScheduledTask:
    task = ScheduledTask(
        id=id,
        title=title,
        description=f"Description for {title}",
        expected_output="Some output",
        tool_id=tool_id,
        tool_params={},
        wave=0,
    )
    task.state = state
    task.result = result or {"result": 42, "success": True}
    task.error = error
    task.execution_time_ms = execution_time_ms
    task.started_at = time.time() - 1
    task.completed_at = time.time()
    return task


class TestReportGenerator:
    def setup_method(self):
        self.generator = ReportGenerator()

    def test_generate_basic_report(self):
        """Generate a report from a single completed task."""
        tasks = {
            "t1": make_completed_task("t1", "Research Tesla")
        }
        report = self.generator.generate(
            execution_id="exec_001",
            goal="Research Tesla",
            tasks=tasks,
            events=[],
        )
        assert isinstance(report, ExecutionReport)
        assert report.execution_id == "exec_001"
        assert report.goal == "Research Tesla"

    def test_report_has_markdown(self):
        """Report should contain non-empty markdown."""
        tasks = {
            "t1": make_completed_task("t1", "Analyze data")
        }
        report = self.generator.generate(
            execution_id="exec_002",
            goal="Analyze data",
            tasks=tasks,
            events=[],
        )
        assert report.report_markdown is not None
        assert len(report.report_markdown) > 0
        # Should contain some markdown
        assert "#" in report.report_markdown or "-" in report.report_markdown

    def test_report_statistics(self):
        """Execution statistics should be accurate."""
        tasks = {
            "t1": make_completed_task("t1", "Task 1"),
            "t2": make_completed_task("t2", "Task 2"),
            "t3": make_completed_task("t3", "Task 3", state=TaskState.FAILED, error="Error"),
        }
        report = self.generator.generate(
            execution_id="exec_003",
            goal="Test stats",
            tasks=tasks,
            events=[],
        )
        stats = report.execution_statistics
        assert stats["total_tasks"] == 3
        assert stats["completed"] == 2
        assert stats["failed"] == 1

    def test_success_rate_calculation(self):
        """Success rate should be computed as completed/total (as percentage or fraction)."""
        tasks = {
            "t1": make_completed_task("t1", "Task 1"),
            "t2": make_completed_task("t2", "Task 2"),
            "t3": make_completed_task("t3", "Task 3"),
            "t4": make_completed_task("t4", "Task 4", state=TaskState.FAILED),
        }
        report = self.generator.generate(
            execution_id="exec_004",
            goal="Calculate success rate",
            tasks=tasks,
            events=[],
        )
        rate = report.execution_statistics["success_rate"]
        # Success rate can be fraction (0.75) or percentage (75.0)
        # Verify it makes sense: either 75.0 or 0.75
        assert rate == 75.0 or abs(rate - 0.75) < 0.01

    def test_empty_tasks_report(self):
        """Report with no tasks should still be generated."""
        report = self.generator.generate(
            execution_id="exec_005",
            goal="Empty goal",
            tasks={},
            events=[],
        )
        assert report is not None
        assert report.execution_statistics["total_tasks"] == 0

    def test_partial_report_flag(self):
        """Partial report should have partial=True."""
        tasks = {
            "t1": make_completed_task("t1", "Partial task")
        }
        report = self.generator.generate(
            execution_id="exec_006",
            goal="Partial run",
            tasks=tasks,
            events=[],
            partial=True,
        )
        assert report.partial is True

    def test_full_report_partial_false(self):
        """Full report should have partial=False."""
        tasks = {
            "t1": make_completed_task("t1", "Complete task")
        }
        report = self.generator.generate(
            execution_id="exec_007",
            goal="Full run",
            tasks=tasks,
            events=[],
            partial=False,
        )
        assert report.partial is False

    def test_actions_performed_from_tasks(self):
        """Actions performed should map to the tasks."""
        tasks = {
            "t1": make_completed_task("t1", "Action 1", tool_id="web_search"),
            "t2": make_completed_task("t2", "Action 2", tool_id="calculator"),
        }
        report = self.generator.generate(
            execution_id="exec_008",
            goal="Test actions",
            tasks=tasks,
            events=[],
        )
        assert len(report.actions_performed) == 2
        tools_used = [a["tool"] for a in report.actions_performed]
        assert "web_search" in tools_used or "calculator" in tools_used

    def test_errors_tracked(self):
        """Failed tasks should appear in errors_encountered."""
        tasks = {
            "t1": make_completed_task("t1", "Bad task", state=TaskState.FAILED, error="Tool timeout"),
        }
        report = self.generator.generate(
            execution_id="exec_009",
            goal="Error tracking",
            tasks=tasks,
            events=[],
        )
        assert len(report.errors_encountered) >= 1
        assert any("timeout" in str(e.get("error", "")).lower()
                   for e in report.errors_encountered)

    def test_to_dict_serializable(self):
        """Report to_dict should produce a serializable dict."""
        import json
        tasks = {
            "t1": make_completed_task("t1", "Dict test")
        }
        report = self.generator.generate(
            execution_id="exec_010",
            goal="Serialization test",
            tasks=tasks,
            events=[],
        )
        d = report.to_dict()
        # Should be JSON serializable
        json_str = json.dumps(d)
        assert len(json_str) > 0

    def test_final_result_not_empty(self):
        """Final result text should not be empty."""
        tasks = {
            "t1": make_completed_task("t1", "Final result test")
        }
        report = self.generator.generate(
            execution_id="exec_011",
            goal="Final result test",
            tasks=tasks,
            events=[],
        )
        assert report.final_result is not None
        assert len(report.final_result) > 0

    def test_tools_used_in_statistics(self):
        """Statistics should include tools_used list."""
        tasks = {
            "t1": make_completed_task("t1", "Tool stats", tool_id="python_executor"),
            "t2": make_completed_task("t2", "Tool stats 2", tool_id="file_writer"),
        }
        report = self.generator.generate(
            execution_id="exec_012",
            goal="Tool usage tracking",
            tasks=tasks,
            events=[],
        )
        tools_used = report.execution_statistics.get("tools_used", [])
        assert isinstance(tools_used, list)


class TestExecutionReport:
    def test_to_dict_has_required_keys(self):
        report = ExecutionReport(
            execution_id="test_id",
            goal="Test goal",
            objective="Test objective",
            actions_performed=[],
            findings=[],
            generated_outputs=[],
            errors_encountered=[],
            execution_statistics={
                "total_tasks": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
                "success_rate": 0.0,
                "total_execution_time_ms": 0,
                "total_execution_time_s": 0.0,
                "total_retries": 0,
                "tools_used": [],
                "partial": False,
            },
            final_result="Done",
            report_markdown="# Report\n\nTest",
        )
        d = report.to_dict()
        required_keys = [
            "execution_id", "goal", "objective", "actions_performed",
            "findings", "generated_outputs", "errors_encountered",
            "execution_statistics", "final_result", "report_markdown",
            "created_at", "partial",
        ]
        for k in required_keys:
            assert k in d, f"Missing key: {k}"
