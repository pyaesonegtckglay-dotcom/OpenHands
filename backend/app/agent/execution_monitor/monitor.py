"""
Execution Monitor — Phase 3
Tracks execution metrics in real-time.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    execution_id: str
    goal: str
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    running_tasks: int = 0
    failed_tasks: int = 0
    completed_tasks: int = 0
    total_tasks: int = 0
    retries: int = 0
    tools_used: list[str] = field(default_factory=list)
    provider_used: str = ""
    success_rate: float = 0.0

    @property
    def elapsed_ms(self) -> int:
        end = self.finished_at or time.time()
        return int((end - self.started_at) * 1000)

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "goal": self.goal[:100],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_ms": self.elapsed_ms,
            "running_tasks": self.running_tasks,
            "failed_tasks": self.failed_tasks,
            "completed_tasks": self.completed_tasks,
            "total_tasks": self.total_tasks,
            "retries": self.retries,
            "tools_used": self.tools_used,
            "provider_used": self.provider_used,
            "success_rate": self.success_rate,
        }


class ExecutionMonitor:
    """Tracks running executions and their metrics."""

    def __init__(self):
        self._metrics: dict[str, ExecutionMetrics] = {}

    def start(self, execution_id: str, goal: str, total_tasks: int) -> ExecutionMetrics:
        m = ExecutionMetrics(
            execution_id=execution_id,
            goal=goal,
            total_tasks=total_tasks,
        )
        self._metrics[execution_id] = m
        return m

    def update(self, execution_id: str, **kwargs) -> None:
        if execution_id in self._metrics:
            m = self._metrics[execution_id]
            for k, v in kwargs.items():
                if hasattr(m, k):
                    setattr(m, k, v)

    def finish(self, execution_id: str, completed: int, failed: int) -> None:
        if execution_id in self._metrics:
            m = self._metrics[execution_id]
            m.finished_at = time.time()
            m.completed_tasks = completed
            m.failed_tasks = failed
            if m.total_tasks > 0:
                m.success_rate = round(completed / m.total_tasks * 100, 1)

    def get(self, execution_id: str) -> Optional[ExecutionMetrics]:
        return self._metrics.get(execution_id)

    def list_all(self) -> list[dict]:
        return [m.to_dict() for m in self._metrics.values()]

    def get_global_stats(self) -> dict:
        all_m = list(self._metrics.values())
        return {
            "total_executions": len(all_m),
            "total_tasks": sum(m.total_tasks for m in all_m),
            "total_completed": sum(m.completed_tasks for m in all_m),
            "total_failed": sum(m.failed_tasks for m in all_m),
            "total_retries": sum(m.retries for m in all_m),
            "avg_success_rate": (
                round(sum(m.success_rate for m in all_m) / len(all_m), 1)
                if all_m else 0.0
            ),
        }


# Singleton
execution_monitor = ExecutionMonitor()
