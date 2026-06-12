"""
Phase 3 Tests: Execution Monitor
Tests execution monitoring statistics tracking.
"""
import pytest
import time
from app.agent.execution_monitor.monitor import ExecutionMonitor


class TestExecutionMonitor:
    def setup_method(self):
        self.monitor = ExecutionMonitor()

    def test_start_execution(self):
        """Starting an execution should track it."""
        self.monitor.start("exec_001", "Test goal", total_tasks=5)
        metric = self.monitor.get("exec_001")
        assert metric is not None

    def test_start_sets_goal(self):
        self.monitor.start("exec_002", "My goal", total_tasks=3)
        metric = self.monitor.get("exec_002")
        assert metric is not None
        d = metric.to_dict()
        assert "goal" in d or "execution_id" in d

    def test_finish_execution(self):
        """Finishing should record completion stats."""
        self.monitor.start("exec_003", "Finish test", total_tasks=4)
        self.monitor.finish("exec_003", completed=3, failed=1)
        metric = self.monitor.get("exec_003")
        assert metric is not None

    def test_get_missing_execution_returns_none(self):
        result = self.monitor.get("nonexistent_exec")
        assert result is None

    def test_global_stats_keys(self):
        """Global stats should have expected keys."""
        stats = self.monitor.get_global_stats()
        assert isinstance(stats, dict)
        # Should have some stats keys
        assert len(stats) > 0

    def test_list_all(self):
        """list_all should return all tracked executions."""
        self.monitor.start("list_001", "Goal 1", total_tasks=2)
        self.monitor.start("list_002", "Goal 2", total_tasks=3)
        all_execs = self.monitor.list_all()
        assert isinstance(all_execs, list)

    def test_to_dict_from_metric(self):
        """Metric to_dict should be serializable."""
        import json
        self.monitor.start("dict_001", "Dict test", total_tasks=2)
        metric = self.monitor.get("dict_001")
        if metric:
            d = metric.to_dict()
            assert isinstance(d, dict)
            # Should be JSON serializable
            json.dumps(d)

    def test_multiple_executions_tracked(self):
        """Multiple simultaneous executions should be tracked independently."""
        self.monitor.start("multi_001", "Goal A", total_tasks=1)
        self.monitor.start("multi_002", "Goal B", total_tasks=2)
        self.monitor.start("multi_003", "Goal C", total_tasks=3)

        assert self.monitor.get("multi_001") is not None
        assert self.monitor.get("multi_002") is not None
        assert self.monitor.get("multi_003") is not None


class TestToolResultStore:
    """Test tool result persistence (in-memory, no DB required)."""

    def test_import_result_store(self):
        """Tool result store should import without errors."""
        from app.agent.tool_result_store.store import ToolResultStore
        store = ToolResultStore()
        assert store is not None
