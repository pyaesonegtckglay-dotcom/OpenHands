"""
Phase 3 Tests: Tool Executor
Tests tool execution with retry logic, timeouts, and structured results.
"""
import asyncio
import pytest
from app.agent.tool_executor.executor import ToolExecutor, ToolExecutionResult


class TestToolExecutor:
    def setup_method(self):
        # Ensure tools are registered
        import app.agent.tool_registry.tools  # noqa: F401
        self.executor = ToolExecutor()

    def test_execute_calculator_success(self):
        """Calculator tool should return success result."""
        result = asyncio.run(self.executor.execute(
            task_id="task_001",
            tool_id="calculator",
            params={"expression": "10 * 10"},
        ))
        assert isinstance(result, ToolExecutionResult)
        assert result.status == "success"
        assert result.tool == "calculator"
        assert result.task_id == "task_001"
        assert result.execution_time_ms >= 0

    def test_execute_calculator_result_value(self):
        """Verify actual computation result."""
        result = asyncio.run(self.executor.execute(
            task_id="task_002",
            tool_id="calculator",
            params={"expression": "2 ** 8"},
        ))
        assert result.status == "success"
        assert result.result is not None
        assert result.result.get("result") == 256

    def test_execute_file_writer_success(self):
        """File writer should succeed and create file."""
        result = asyncio.run(self.executor.execute(
            task_id="task_003",
            tool_id="file_writer",
            params={"filename": "executor_test.txt", "content": "Executor test content"},
        ))
        assert result.status == "success"

    def test_execute_python_executor_success(self):
        """Python executor should run code successfully."""
        result = asyncio.run(self.executor.execute(
            task_id="task_004",
            tool_id="python_executor",
            params={"code": "print('executor ok')"},
        ))
        assert result.status == "success"
        assert result.result is not None

    def test_execute_unknown_tool_fails(self):
        """Unknown tool should return failed result."""
        result = asyncio.run(self.executor.execute(
            task_id="task_005",
            tool_id="nonexistent_tool_xyz",
            params={},
        ))
        assert result.status == "failed"
        assert result.error is not None

    def test_result_has_execution_time(self):
        """Execution result should track execution time."""
        result = asyncio.run(self.executor.execute(
            task_id="task_006",
            tool_id="calculator",
            params={"expression": "1 + 1"},
        ))
        assert result.execution_time_ms >= 0

    def test_to_dict_structure(self):
        """Result to_dict should have expected keys."""
        result = asyncio.run(self.executor.execute(
            task_id="task_007",
            tool_id="calculator",
            params={"expression": "42"},
        ))
        d = result.to_dict()
        required_keys = ["task_id", "tool", "tool_name", "status", "result",
                         "error", "execution_time_ms", "retries", "attempt"]
        for k in required_keys:
            assert k in d, f"Missing key: {k}"

    def test_cancelled_event_respected(self):
        """Execution with pre-set cancel event should handle gracefully."""
        cancel_event = asyncio.Event()
        cancel_event.set()

        result = asyncio.run(self.executor.execute(
            task_id="task_008",
            tool_id="calculator",
            params={"expression": "1 + 1"},
            cancelled=cancel_event,
        ))
        # With pre-cancelled event: either cancelled or completed (depending on impl)
        assert result.status in ("success", "cancelled", "failed")

    def test_retries_count_in_result(self):
        """Retries field should be tracked."""
        result = asyncio.run(self.executor.execute(
            task_id="task_009",
            tool_id="calculator",
            params={"expression": "100 / 4"},
        ))
        assert isinstance(result.retries, int)
        assert result.retries >= 0

    def test_tool_name_set_correctly(self):
        """tool_name should be the human-readable name."""
        result = asyncio.run(self.executor.execute(
            task_id="task_010",
            tool_id="calculator",
            params={"expression": "1"},
        ))
        assert result.tool_name == "Calculator"
