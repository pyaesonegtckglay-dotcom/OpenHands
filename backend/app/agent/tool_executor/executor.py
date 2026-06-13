"""
Tool Executor — Phase 3
Executes tools with retry logic, timeouts, and structured results.

Retry Strategy: 1s → 3s → 5s (max 3 retries)
Default timeout: 30s, Long-running: 120s
"""
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.agent.tool_registry import tool_registry

logger = logging.getLogger(__name__)

RETRY_DELAYS = [1, 3, 5]  # seconds
DEFAULT_TIMEOUT = 30
LONG_TIMEOUT = 120
MAX_RETRIES = 3


@dataclass
class ToolExecutionResult:
    """Structured result from tool execution."""
    task_id: str
    tool: str
    tool_name: str
    status: str  # "success" | "failed" | "timeout" | "cancelled"
    result: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    retries: int = 0
    attempt: int = 1

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "tool": self.tool,
            "tool_name": self.tool_name,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "retries": self.retries,
            "attempt": self.attempt,
        }


class ToolExecutor:
    """
    Executes tools with:
    - Automatic retry on timeout/failure
    - Configurable timeouts (default 30s, long-running 120s)
    - Structured result output
    - Cancellation support
    """

    LONG_RUNNING_TOOLS = {"python_executor", "ai_synthesis", "http_request"}

    async def execute(
        self,
        task_id: str,
        tool_id: str,
        params: dict,
        timeout: Optional[int] = None,
        max_retries: int = MAX_RETRIES,
        cancelled: Optional[asyncio.Event] = None,
    ) -> ToolExecutionResult:
        """
        Execute a tool with retry logic.

        Args:
            task_id: Unique task ID for tracking
            tool_id: Tool to execute
            params: Tool input parameters
            timeout: Override default timeout
            max_retries: Max retry attempts (default 3)
            cancelled: Optional asyncio.Event to signal cancellation

        Returns:
            ToolExecutionResult with status, result, timing
        """
        tool = tool_registry.get(tool_id)
        if not tool:
            return ToolExecutionResult(
                task_id=task_id,
                tool=tool_id,
                tool_name=tool_id,
                status="failed",
                result=None,
                error=f"Tool '{tool_id}' not found in registry",
            )

        if not tool.enabled:
            return ToolExecutionResult(
                task_id=task_id,
                tool=tool_id,
                tool_name=tool.name,
                status="failed",
                result=None,
                error=f"Tool '{tool_id}' is disabled",
            )

        if not tool.handler:
            return ToolExecutionResult(
                task_id=task_id,
                tool=tool_id,
                tool_name=tool.name,
                status="failed",
                result=None,
                error=f"Tool '{tool_id}' has no handler",
            )

        # Determine timeout
        if timeout is None:
            timeout = LONG_TIMEOUT if tool_id in self.LONG_RUNNING_TOOLS else DEFAULT_TIMEOUT

        last_error = None
        for attempt in range(1, max_retries + 2):  # +2 because range is exclusive
            # Check cancellation
            if cancelled and cancelled.is_set():
                return ToolExecutionResult(
                    task_id=task_id,
                    tool=tool_id,
                    tool_name=tool.name,
                    status="cancelled",
                    result=None,
                    error="Task cancelled by user",
                    retries=attempt - 1,
                    attempt=attempt,
                )

            start_time = time.monotonic()

            try:
                logger.info(f"[ToolExecutor] Executing {tool_id} (attempt {attempt}/{max_retries + 1}) task={task_id}")

                # Execute with timeout
                result = await asyncio.wait_for(
                    tool.handler(params),
                    timeout=timeout,
                )

                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                logger.info(f"[ToolExecutor] {tool_id} completed in {elapsed_ms}ms")

                return ToolExecutionResult(
                    task_id=task_id,
                    tool=tool_id,
                    tool_name=tool.name,
                    status="success",
                    result=result,
                    execution_time_ms=elapsed_ms,
                    retries=attempt - 1,
                    attempt=attempt,
                )

            except asyncio.TimeoutError:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                last_error = f"Timed out after {timeout}s"
                logger.warning(f"[ToolExecutor] {tool_id} timed out (attempt {attempt})")

                if attempt <= max_retries:
                    delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
                    logger.info(f"[ToolExecutor] Retrying {tool_id} in {delay}s...")
                    await asyncio.sleep(delay)
                    continue

                return ToolExecutionResult(
                    task_id=task_id,
                    tool=tool_id,
                    tool_name=tool.name,
                    status="timeout",
                    result=None,
                    error=last_error,
                    execution_time_ms=elapsed_ms,
                    retries=attempt - 1,
                    attempt=attempt,
                )

            except Exception as e:
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                error_type = type(e).__name__
                last_error = f"{error_type}: {str(e)}"
                logger.warning(f"[ToolExecutor] {tool_id} failed (attempt {attempt}): {last_error}")

                # Retry on transient errors
                if attempt <= max_retries and self._is_retryable(e):
                    delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
                    logger.info(f"[ToolExecutor] Retrying {tool_id} in {delay}s... (retryable error)")
                    await asyncio.sleep(delay)
                    continue

                return ToolExecutionResult(
                    task_id=task_id,
                    tool=tool_id,
                    tool_name=tool.name,
                    status="failed",
                    result=None,
                    error=last_error,
                    execution_time_ms=elapsed_ms,
                    retries=attempt - 1,
                    attempt=attempt,
                )

        # Should not reach here, but safeguard
        return ToolExecutionResult(
            task_id=task_id,
            tool=tool_id,
            tool_name=tool.name,
            status="failed",
            result=None,
            error=last_error or "Unknown error after retries",
            retries=max_retries,
        )

    def _is_retryable(self, error: Exception) -> bool:
        """Determine if an error is worth retrying."""
        retryable_types = (
            ConnectionError, TimeoutError, OSError,
        )
        retryable_messages = ["rate limit", "timeout", "connection", "temporarily", "503", "429", "502"]

        if isinstance(error, retryable_types):
            return True

        error_str = str(error).lower()
        return any(msg in error_str for msg in retryable_messages)
