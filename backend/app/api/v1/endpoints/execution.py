"""
Phase 3 — Execution API Endpoints
POST /execution/start
POST /execution/stop
GET  /execution/{id}
GET  /execution/{id}/events  (SSE)
GET  /execution/{id}/report
GET  /execution/history
"""
import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from asyncpg import Connection

from app.database.connection import get_db
from app.core.security import get_current_user
from app.agent.execution_engine import ExecutionEngine
from app.agent.activity_stream import ActivityStream
from app.agent.execution_monitor import execution_monitor
from app.agent.tool_registry import tool_registry

logger = logging.getLogger(__name__)

execution_router = APIRouter(prefix="/execution", tags=["Phase 3 - Execution"])

# In-memory store for active executions (execution_id → {stream, cancel_event, task})
_active_executions: dict[str, dict] = {}


# ─── Request / Response Models ─────────────────────────────────────────────────

class StartExecutionRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=5000, description="The goal to execute")
    feature_flags: Optional[dict] = Field(default=None, description="Feature flags")


class StopExecutionRequest(BaseModel):
    execution_id: str


class ExecutionStartResponse(BaseModel):
    execution_id: str
    goal: str
    status: str
    stream_url: str
    message: str


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@execution_router.post("/start", response_model=ExecutionStartResponse)
async def start_execution(
    data: StartExecutionRequest,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Start a new execution. Returns execution_id and SSE stream URL.
    The actual execution runs in the background.
    Connect to /execution/{id}/events to receive real-time events.
    """
    execution_id = str(uuid.uuid4())
    user_id = current_user["user_id"]
    goal = data.goal.strip()

    if not goal:
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    # Create stream and cancel event
    stream = ActivityStream(execution_id)
    cancel_event = asyncio.Event()

    # Store in active executions
    _active_executions[execution_id] = {
        "stream": stream,
        "cancel_event": cancel_event,
        "goal": goal,
        "user_id": user_id,
        "status": "starting",
        "task": None,
    }

    # Save to DB
    try:
        import uuid as _uuid
        try:
            user_uuid = _uuid.UUID(str(user_id))
        except Exception:
            user_uuid = user_id
        await conn.execute(
            """INSERT INTO task_executions
               (id, user_id, goal, status, created_at)
               VALUES ($1,$2,$3,'STARTED', NOW())""",
            execution_id, user_uuid, goal[:500],
        )
    except Exception as e:
        logger.warning(f"[Execution] Failed to save execution to DB: {e}")

    # Launch execution in background (non-blocking)
    # We use a separate DB connection for background task
    asyncio.create_task(
        _run_execution_background(execution_id, goal, user_id, stream, cancel_event),
        name=f"exec_{execution_id[:8]}",
    )

    _active_executions[execution_id]["status"] = "running"

    return ExecutionStartResponse(
        execution_id=execution_id,
        goal=goal,
        status="started",
        stream_url=f"/api/v1/execution/{execution_id}/events",
        message="Execution started. Connect to stream_url for real-time events.",
    )


async def _run_execution_background(
    execution_id: str,
    goal: str,
    user_id: str,
    stream: ActivityStream,
    cancel_event: asyncio.Event,
) -> None:
    """Run the execution pipeline in background with its own DB connection."""
    from app.database.connection import get_pool

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            engine = ExecutionEngine()
            report = await engine.execute(
                execution_id=execution_id,
                goal=goal,
                user_id=str(user_id),
                conn=conn,
                stream=stream,
                cancel_event=cancel_event,
            )

            # Update execution status in DB
            try:
                status = "CANCELLED" if cancel_event.is_set() else "COMPLETED"
                await conn.execute(
                    "UPDATE task_executions SET status=$1, completed_at=NOW() WHERE id=$2",
                    status, execution_id,
                )
            except Exception as e:
                logger.warning(f"[Execution] Failed to update status: {e}")

            if execution_id in _active_executions:
                _active_executions[execution_id]["status"] = "completed"
                _active_executions[execution_id]["report"] = report

    except asyncio.CancelledError:
        logger.info(f"[Execution] Background task {execution_id} cancelled")
        if execution_id in _active_executions:
            _active_executions[execution_id]["status"] = "cancelled"
    except Exception as e:
        logger.error(f"[Execution] Background task {execution_id} failed: {e}", exc_info=True)
        if execution_id in _active_executions:
            _active_executions[execution_id]["status"] = "failed"
        await stream.emit("error", {"error": str(e)}, level="error")
    finally:
        stream.close()
        logger.info(f"[Execution] {execution_id} background task finished")


@execution_router.get("/{execution_id}/events")
async def stream_execution_events(
    execution_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    SSE stream for real-time execution events.
    Returns text/event-stream.
    """
    exec_data = _active_executions.get(execution_id)
    if not exec_data:
        # Check DB for historical execution
        raise HTTPException(
            status_code=404,
            detail=f"Execution {execution_id} not found or already completed"
        )

    stream: ActivityStream = exec_data["stream"]

    async def event_stream():
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'execution_id': execution_id})}\n\n"

        # Stream all events
        async for event_data in stream.sse_generator():
            if await request.is_disconnected():
                break
            yield event_data

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@execution_router.post("/stop")
async def stop_execution(
    data: StopExecutionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Stop an active execution."""
    exec_data = _active_executions.get(data.execution_id)
    if not exec_data:
        raise HTTPException(status_code=404, detail="Execution not found or already completed")

    cancel_event: asyncio.Event = exec_data.get("cancel_event")
    if cancel_event:
        cancel_event.set()
        _active_executions[data.execution_id]["status"] = "cancelling"

    return {"execution_id": data.execution_id, "status": "cancelling", "message": "Stop signal sent"}


@execution_router.get("/history")
async def get_execution_history(
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    """Get execution history for the current user."""
    user_id = current_user["user_id"]
    try:
        import uuid as _uuid
        try:
            user_uuid = _uuid.UUID(str(user_id))
        except Exception:
            user_uuid = user_id
        rows = await conn.fetch(
            """SELECT id, goal, status, created_at, completed_at
               FROM task_executions
               WHERE user_id = $1
               ORDER BY created_at DESC
               LIMIT $2 OFFSET $3""",
            user_uuid, limit, offset,
        )
        executions = []
        for row in rows:
            e = dict(row)
            e["created_at"] = e["created_at"].isoformat() if e.get("created_at") else None
            e["completed_at"] = e["completed_at"].isoformat() if e.get("completed_at") else None
            # Enrich with live data if available
            live = _active_executions.get(e["id"])
            if live:
                e["live_status"] = live.get("status", "unknown")
            executions.append(e)
        return {"executions": executions, "total": len(executions)}
    except Exception as e:
        logger.error(f"[Execution] History query failed: {e}")
        return {"executions": [], "total": 0}


@execution_router.get("/{execution_id}")
async def get_execution(
    execution_id: str,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get execution details including current status and tasks."""
    # Check live executions first
    live = _active_executions.get(execution_id)

    try:
        row = await conn.fetchrow(
            "SELECT * FROM task_executions WHERE id = $1",
            execution_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Execution not found")

        result = dict(row)
        result["created_at"] = result["created_at"].isoformat() if result.get("created_at") else None
        result["completed_at"] = result["completed_at"].isoformat() if result.get("completed_at") else None

        # Add live metrics
        metrics = execution_monitor.get(execution_id)
        if metrics:
            result["metrics"] = metrics.to_dict()

        if live:
            result["live_status"] = live.get("status", "unknown")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Execution] Get execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@execution_router.get("/{execution_id}/report")
async def get_execution_report(
    execution_id: str,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the final execution report."""
    # Check live report first
    live = _active_executions.get(execution_id)
    if live and live.get("report"):
        return live["report"].to_dict()

    # Fetch from DB
    try:
        row = await conn.fetchrow(
            "SELECT * FROM task_reports WHERE execution_id = $1 ORDER BY created_at DESC LIMIT 1",
            execution_id,
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Report not yet available. Execution may still be running."
            )
        result = dict(row)
        # Parse JSON data if stored
        if result.get("report_data"):
            try:
                return json.loads(result["report_data"])
            except Exception:
                pass
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Execution] Get report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@execution_router.get("/tools/registry")
async def get_tool_registry(
    current_user: dict = Depends(get_current_user),
):
    """Get all registered tools."""
    return {
        "tools": tool_registry.to_dict(),
        "total": len(tool_registry.list_tools()),
        "enabled": len(tool_registry.list_enabled()),
    }


@execution_router.get("/monitor/stats")
async def get_monitor_stats(
    current_user: dict = Depends(get_current_user),
):
    """Get global execution monitor statistics."""
    return {
        "global": execution_monitor.get_global_stats(),
        "active_executions": len([
            e for e in _active_executions.values()
            if e.get("status") in ("starting", "running")
        ]),
        "recent": execution_monitor.list_all()[-10:],
    }


@execution_router.get("/debug/tables")
async def debug_tables(
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Debug: check all table schemas and row counts."""
    try:
        import uuid as _uuid
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"
        )
        table_names = [r["table_name"] for r in tables]

        result: dict = {"tables": table_names, "schemas": {}, "counts": {}}
        for tname in ["executions", "task_executions", "tool_results", "execution_events",
                       "task_tool_results", "task_execution_events", "reports", "task_reports"]:
            if tname in table_names:
                cols = await conn.fetch(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=$1 ORDER BY ordinal_position",
                    tname,
                )
                result["schemas"][tname] = {r["column_name"]: r["data_type"] for r in cols}
                cnt = await conn.fetchval(f"SELECT COUNT(*) FROM {tname}")
                result["counts"][tname] = cnt

        return result
    except Exception as e:
        return {"error": str(e)}
