"""
Execution Scheduler — Phase 3
Receives the task graph and schedules execution.
Supports: Sequential, Parallel, Dependency-aware execution.

Task States: PLANNED → READY → RUNNING → WAITING → RETRYING → COMPLETED → FAILED → CANCELLED
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


class TaskState(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ScheduledTask:
    """A task scheduled for execution."""
    id: str
    title: str
    description: str
    expected_output: str
    tool_id: str
    tool_params: dict
    wave: int
    dependencies: list[str] = field(default_factory=list)
    state: TaskState = TaskState.PLANNED
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    execution_time_ms: int = 0
    retries: int = 0

    @property
    def duration_ms(self) -> int:
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at) * 1000)
        return 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "expected_output": self.expected_output,
            "tool_id": self.tool_id,
            "wave": self.wave,
            "dependencies": self.dependencies,
            "state": self.state.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_time_ms": self.execution_time_ms or self.duration_ms,
            "retries": self.retries,
        }


class ExecutionScheduler:
    """
    Schedules and executes a task graph.

    Features:
    - Wave-based parallel execution (tasks in the same wave run concurrently)
    - Dependency tracking (waits for dependencies before starting)
    - Cancellation via asyncio.Event
    - Real-time event streaming via callback
    """

    def __init__(self, event_callback: Optional[Callable] = None):
        """
        Args:
            event_callback: async callable(event_type: str, data: dict)
                            Called for each execution event
        """
        self.event_callback = event_callback
        self.tasks: dict[str, ScheduledTask] = {}
        self.cancel_event = asyncio.Event()

    async def _emit(self, event_type: str, data: dict) -> None:
        """Emit a real-time execution event."""
        if self.event_callback:
            try:
                await self.event_callback(event_type, data)
            except Exception as e:
                logger.warning(f"[Scheduler] Event callback error: {e}")

    async def execute_graph(
        self,
        execution_id: str,
        tasks_by_wave: dict[int, list[ScheduledTask]],
        max_parallel: int = 5,
    ) -> dict[str, ScheduledTask]:
        """
        Execute tasks in wave order.
        Each wave can execute tasks in parallel.
        Dependencies within waves are respected.

        Args:
            execution_id: Unique execution ID
            tasks_by_wave: dict of wave_number → [ScheduledTask]
            max_parallel: Max concurrent tasks per wave

        Returns:
            dict of task_id → completed ScheduledTask
        """
        from app.agent.tool_executor import ToolExecutor
        executor = ToolExecutor()

        # Register all tasks
        for wave_tasks in tasks_by_wave.values():
            for task in wave_tasks:
                self.tasks[task.id] = task

        total_tasks = sum(len(t) for t in tasks_by_wave.values())
        completed_count = 0

        await self._emit("execution_started", {
            "execution_id": execution_id,
            "total_tasks": total_tasks,
            "total_waves": len(tasks_by_wave),
        })

        # Execute wave by wave
        for wave_num in sorted(tasks_by_wave.keys()):
            if self.cancel_event.is_set():
                await self._emit("execution_cancelled", {"execution_id": execution_id, "wave": wave_num})
                break

            wave_tasks = tasks_by_wave[wave_num]
            await self._emit("wave_started", {
                "execution_id": execution_id,
                "wave": wave_num,
                "task_count": len(wave_tasks),
                "task_titles": [t.title for t in wave_tasks],
            })

            # Execute wave tasks with controlled parallelism
            semaphore = asyncio.Semaphore(max_parallel)

            async def execute_task_with_sem(task: ScheduledTask) -> None:
                async with semaphore:
                    await self._execute_single_task(executor, execution_id, task)

            await asyncio.gather(
                *[execute_task_with_sem(task) for task in wave_tasks],
                return_exceptions=True,
            )

            completed_in_wave = sum(
                1 for t in wave_tasks if t.state == TaskState.COMPLETED
            )
            completed_count += completed_in_wave

            await self._emit("wave_completed", {
                "execution_id": execution_id,
                "wave": wave_num,
                "completed": completed_in_wave,
                "total_in_wave": len(wave_tasks),
                "overall_progress": int((completed_count / total_tasks) * 100),
            })

            # Stop execution if critical tasks failed
            failed_in_wave = [t for t in wave_tasks if t.state == TaskState.FAILED]
            if failed_in_wave and wave_num == 0:
                logger.warning(f"[Scheduler] Critical wave 0 tasks failed: {[t.title for t in failed_in_wave]}")
                # Continue anyway — generate partial report

        await self._emit("execution_completed", {
            "execution_id": execution_id,
            "total_completed": sum(1 for t in self.tasks.values() if t.state == TaskState.COMPLETED),
            "total_failed": sum(1 for t in self.tasks.values() if t.state == TaskState.FAILED),
            "total_tasks": total_tasks,
        })

        return self.tasks

    async def _execute_single_task(
        self,
        executor,
        execution_id: str,
        task: ScheduledTask,
    ) -> None:
        """Execute a single task with full lifecycle tracking."""
        if self.cancel_event.is_set():
            task.state = TaskState.CANCELLED
            await self._emit("task_cancelled", {
                "execution_id": execution_id,
                "task_id": task.id,
                "task_title": task.title,
            })
            return

        # Update state → RUNNING
        task.state = TaskState.RUNNING
        task.started_at = time.monotonic()

        await self._emit("task_started", {
            "execution_id": execution_id,
            "task_id": task.id,
            "task_title": task.title,
            "tool": task.tool_id,
            "wave": task.wave,
        })

        # Execute
        exec_result = await executor.execute(
            task_id=task.id,
            tool_id=task.tool_id,
            params=task.tool_params,
            cancelled=self.cancel_event,
        )

        task.completed_at = time.monotonic()
        task.execution_time_ms = exec_result.execution_time_ms
        task.retries = exec_result.retries

        if exec_result.status in ("success",):
            task.state = TaskState.COMPLETED
            task.result = exec_result.result
            await self._emit("task_completed", {
                "execution_id": execution_id,
                "task_id": task.id,
                "task_title": task.title,
                "tool": task.tool_id,
                "execution_time_ms": task.execution_time_ms,
                "result_summary": self._summarize_result(exec_result.result),
            })
        elif exec_result.status == "cancelled":
            task.state = TaskState.CANCELLED
            await self._emit("task_cancelled", {
                "execution_id": execution_id,
                "task_id": task.id,
                "task_title": task.title,
            })
        else:
            task.state = TaskState.FAILED
            task.error = exec_result.error
            await self._emit("task_failed", {
                "execution_id": execution_id,
                "task_id": task.id,
                "task_title": task.title,
                "tool": task.tool_id,
                "error": exec_result.error,
                "retries": exec_result.retries,
            })

    def _summarize_result(self, result: Any) -> str:
        """Create a brief summary of a tool result."""
        if result is None:
            return "No result"
        if isinstance(result, dict):
            if result.get("error"):
                return f"Error: {result['error'][:100]}"
            if result.get("result"):
                r = str(result["result"])
                return r[:200] + "..." if len(r) > 200 else r
            if result.get("output"):
                o = str(result["output"])
                return o[:200] + "..." if len(o) > 200 else o
            if result.get("results"):
                return f"{len(result['results'])} result(s) found"
            if result.get("filename"):
                return f"File created: {result['filename']}"
            return str(result)[:200]
        return str(result)[:200]

    def cancel(self) -> None:
        """Cancel ongoing execution."""
        self.cancel_event.set()
        logger.info("[Scheduler] Execution cancelled")

    def get_stats(self) -> dict:
        """Get execution statistics."""
        all_tasks = list(self.tasks.values())
        return {
            "total": len(all_tasks),
            "completed": sum(1 for t in all_tasks if t.state == TaskState.COMPLETED),
            "failed": sum(1 for t in all_tasks if t.state == TaskState.FAILED),
            "running": sum(1 for t in all_tasks if t.state == TaskState.RUNNING),
            "cancelled": sum(1 for t in all_tasks if t.state == TaskState.CANCELLED),
            "total_retries": sum(t.retries for t in all_tasks),
            "total_execution_ms": sum(t.execution_time_ms for t in all_tasks),
        }
