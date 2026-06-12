"""
Activity Stream — Phase 3
Real-time execution event streaming.
Every event is emitted immediately — no batching.
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger(__name__)

# Human-readable event messages
EVENT_MESSAGES = {
    "intent_detected": "Intent detected",
    "planning_started": "Planning started",
    "plan_generated": "Plan generated",
    "task_graph_created": "Task graph created",
    "execution_started": "Execution started",
    "wave_started": "Running wave {wave}",
    "task_started": "Running: {task_title}",
    "tool_selected": "Using tool: {tool}",
    "tool_running": "Tool executing: {tool}",
    "task_completed": "Completed: {task_title}",
    "task_failed": "Failed: {task_title}",
    "task_cancelled": "Cancelled: {task_title}",
    "wave_completed": "Wave {wave} complete — {completed}/{total_in_wave} tasks",
    "execution_completed": "All tasks complete",
    "execution_cancelled": "Execution stopped by user",
    "report_generating": "Generating final report…",
    "report_complete": "Report ready",
    "error": "Error occurred",
}


@dataclass
class ActivityEvent:
    """A real-time execution event."""
    id: str
    execution_id: str
    event_type: str
    message: str
    data: dict
    timestamp: float = field(default_factory=time.time)
    level: str = "info"  # info | success | warning | error

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "event_type": self.event_type,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
            "timestamp_str": self._format_ts(),
            "level": self.level,
        }

    def _format_ts(self) -> str:
        from datetime import datetime
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    def to_sse(self) -> str:
        """Format as SSE data line."""
        return f"data: {json.dumps(self.to_dict())}\n\n"


class ActivityStream:
    """
    Real-time event stream for execution monitoring.

    Usage:
        stream = ActivityStream(execution_id)
        await stream.emit("task_started", {"task_title": "Search Tesla"})

        # For SSE endpoint:
        async for event_str in stream.sse_generator():
            yield event_str
    """

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._events: list[ActivityEvent] = []
        self._closed = False
        self._event_counter = 0

    async def emit(self, event_type: str, data: dict = None, level: str = "info") -> ActivityEvent:
        """Emit an event immediately to the stream."""
        data = data or {}
        self._event_counter += 1

        # Build human-readable message
        template = EVENT_MESSAGES.get(event_type, event_type.replace("_", " ").title())
        try:
            message = template.format(**data)
        except (KeyError, IndexError):
            message = template

        event = ActivityEvent(
            id=f"evt_{self._event_counter:04d}",
            execution_id=self.execution_id,
            event_type=event_type,
            message=message,
            data=data,
            level=level,
        )

        self._events.append(event)
        logger.info(f"[ActivityStream] {event.timestamp_str if hasattr(event, 'timestamp_str') else ''} {event_type}: {message}")

        # Put in queue (non-blocking)
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"[ActivityStream] Queue full, dropping event: {event_type}")

        return event

    def close(self) -> None:
        """Signal stream is complete."""
        self._closed = True
        try:
            self._queue.put_nowait(None)  # Sentinel value
        except asyncio.QueueFull:
            pass

    def get_all_events(self) -> list[ActivityEvent]:
        """Get all events emitted so far."""
        return list(self._events)

    async def sse_generator(self, timeout: float = 300.0) -> AsyncGenerator[str, None]:
        """
        Async generator that yields SSE-formatted events.
        Used by FastAPI StreamingResponse.
        """
        start = time.monotonic()
        last_keepalive = time.monotonic()

        while True:
            # Timeout check
            if time.monotonic() - start > timeout:
                yield f"data: {json.dumps({'type': 'timeout', 'message': 'Stream timeout'})}\n\n"
                break

            try:
                # Non-blocking get with short timeout for keepalive
                event = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                # Send keepalive
                yield "data: [KEEPALIVE]\n\n"
                continue

            # Sentinel = stream closed
            if event is None:
                yield f"data: {json.dumps({'type': 'stream_end', 'execution_id': self.execution_id})}\n\n"
                break

            yield event.to_sse()

            # Send keepalive if needed
            now = time.monotonic()
            if now - last_keepalive > 15:
                yield "data: [KEEPALIVE]\n\n"
                last_keepalive = now
