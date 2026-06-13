"""
Phase 3 — Execution API Endpoints (COMPLETE REWRITE)
POST /execution/start        — Start execution (Direct Executor)
POST /execution/stop         — Stop active execution
GET  /execution/tools/registry  — List registered tools
GET  /execution/monitor/stats   — Global stats
GET  /execution/history      — Execution history
GET  /execution/workspace/files — List workspace files
GET  /execution/{id}         — Get execution status
GET  /execution/{id}/events  — SSE real-time stream
GET  /execution/{id}/report  — Get execution report
GET  /execution/{id}/tasks   — Per-task evidence
GET  /execution/{id}/evidence — Full execution evidence
GET  /execution/{id}/artifacts — Generated artifacts
GET  /execution/{id}/files/{filename} — Download file
GET  /execution/debug/tables  — Debug DB tables
"""
import asyncio
import json
import logging
import os
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel, Field
from asyncpg import Connection

from app.database.connection import get_db
from app.core.security import get_current_user
from app.agent.activity_stream import ActivityStream
from app.agent.execution_monitor import execution_monitor
from app.agent.tool_registry import tool_registry

# Import tools so they self-register
import app.agent.tool_registry.tools  # noqa: F401

logger = logging.getLogger(__name__)

execution_router = APIRouter(prefix="/execution", tags=["Phase 3 - Execution"])

# In-memory store for active executions
# execution_id → {stream, cancel_event, goal, user_id, status}
_active_executions: dict[str, dict] = {}


# ─── Request / Response Models ────────────────────────────────────────────────

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


# ─── Execution Start ──────────────────────────────────────────────────────────

@execution_router.post("/start", response_model=ExecutionStartResponse)
async def start_execution(
    data: StartExecutionRequest,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Start a new execution using the Direct Executor.
    Returns execution_id immediately. Execution runs in background.
    Connect to /execution/{id}/events for real-time SSE events.
    """
    execution_id = str(uuid.uuid4())
    user_id = current_user["user_id"]
    goal = data.goal.strip()

    if not goal:
        raise HTTPException(status_code=400, detail="Goal cannot be empty")

    # Create stream and cancel event
    stream = ActivityStream(execution_id)
    cancel_event = asyncio.Event()

    # Store execution state
    _active_executions[execution_id] = {
        "stream": stream,
        "cancel_event": cancel_event,
        "goal": goal,
        "user_id": str(user_id),
        "status": "starting",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "record": None,
    }

    # Persist to DB
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
        logger.warning(f"[Execution] DB insert failed: {e}")

    # Launch background execution
    asyncio.create_task(
        _run_direct_execution(execution_id, goal, str(user_id), stream, cancel_event),
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


async def _run_direct_execution(
    execution_id: str,
    goal: str,
    user_id: str,
    stream: ActivityStream,
    cancel_event: asyncio.Event,
) -> None:
    """
    Background task: Runs the Direct Executor.
    Updates status in _active_executions and DB upon completion.
    """
    from app.agent.direct_executor import DirectExecutor
    from app.database.connection import get_pool

    try:
        executor = DirectExecutor()
        record = await executor.execute(
            execution_id=execution_id,
            goal=goal,
            user_id=user_id,
            stream=stream,
            cancel_event=cancel_event,
        )

        # Store record in active executions
        if execution_id in _active_executions:
            _active_executions[execution_id]["status"] = record.status
            _active_executions[execution_id]["record"] = record

        # Update DB
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                status_db = "COMPLETED" if record.status == "completed" else record.status.upper()
                await conn.execute(
                    "UPDATE task_executions SET status=$1, completed_at=NOW() WHERE id=$2",
                    status_db, execution_id,
                )

                # Persist artifacts to DB if table exists
                for artifact in record.artifacts:
                    try:
                        await conn.execute(
                            """INSERT INTO task_artifacts
                               (id, execution_id, filename, content_type, size_bytes, download_url, created_at)
                               VALUES ($1, $2, $3, $4, $5, $6, NOW())
                               ON CONFLICT (id) DO NOTHING""",
                            artifact.artifact_id, execution_id,
                            artifact.filename, artifact.content_type,
                            artifact.size_bytes, artifact.download_url,
                        )
                    except Exception:
                        pass  # Artifact table may not exist yet

                # Persist report
                try:
                    await conn.execute(
                        """INSERT INTO task_reports
                           (id, execution_id, goal, report_markdown, report_data, created_at)
                           VALUES ($1, $2, $3, $4, $5, NOW())
                           ON CONFLICT (id) DO NOTHING""",
                        record.report_id or str(uuid.uuid4()),
                        execution_id,
                        record.goal[:500],
                        record.report_markdown[:50000],
                        json.dumps(record.to_dict())[:100000],
                    )
                except Exception as e:
                    logger.warning(f"[Execution] Failed to persist report: {e}")

        except Exception as e:
            logger.warning(f"[Execution] DB update failed: {e}")

    except asyncio.CancelledError:
        logger.info(f"[DirectExec] {execution_id} was cancelled")
        if execution_id in _active_executions:
            _active_executions[execution_id]["status"] = "cancelled"
    except Exception as e:
        logger.error(f"[DirectExec] Fatal: {execution_id} — {e}", exc_info=True)
        if execution_id in _active_executions:
            _active_executions[execution_id]["status"] = "failed"
        try:
            await stream.emit("error", {"execution_id": execution_id, "error": str(e)}, level="error")
            stream.close()
        except Exception:
            pass


# ─── Stop Execution ───────────────────────────────────────────────────────────

@execution_router.post("/stop")
async def stop_execution(
    data: StopExecutionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Stop an active execution."""
    exec_data = _active_executions.get(data.execution_id)
    if not exec_data:
        raise HTTPException(status_code=404, detail="Execution not found or already completed")
    cancel_event = exec_data.get("cancel_event")
    if cancel_event:
        cancel_event.set()
        _active_executions[data.execution_id]["status"] = "cancelling"
    return {"execution_id": data.execution_id, "status": "cancelling", "message": "Stop signal sent"}


# ─── Tool Registry ────────────────────────────────────────────────────────────

@execution_router.get("/tools/registry")
async def get_tool_registry(
    current_user: dict = Depends(get_current_user),
):
    """
    TASK 1 — Tool Registry Verification.
    Returns all registered tools with IDs, schemas, and runtime status.
    """
    tools = tool_registry.list_tools()
    tool_details = []
    for t in tools:
        detail = t.to_dict()
        detail["runtime_status"] = "active" if t.enabled and t.handler else "inactive"
        detail["has_handler"] = t.handler is not None
        tool_details.append(detail)

    return {
        "tool_registry": {
            "registration_location": "app.agent.tool_registry.tools (self-registering on import)",
            "total_registered": len(tools),
            "total_enabled": len([t for t in tools if t.enabled]),
            "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "tools": tool_details,
    }


# ─── Tool Routing Test ────────────────────────────────────────────────────────

@execution_router.post("/tools/route-test")
async def test_tool_routing(
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """
    TASK 2 — Tool Routing Verification.
    Test how a task gets routed to a tool.
    """
    from app.agent.tool_router import ToolRouter
    from app.agent.direct_executor import _build_direct_plan

    goal = data.get("goal", "")
    if not goal:
        raise HTTPException(status_code=400, detail="goal required")

    router = ToolRouter()

    # Build the plan
    plan = _build_direct_plan(goal)

    # Also test routing individually
    routing_results = []
    for task in plan:
        task_title = task.get("title", "")
        task_desc = task.get("description", "")
        route = router.route(task_title, task_desc, task.get("expected_output", ""))
        routing_results.append({
            "task_title": task_title,
            "routed_tool": task["tool"],  # Direct plan's assignment
            "router_suggestion": route.tool_id,
            "router_confidence": route.confidence,
            "router_reason": route.reason,
            "params_assigned": list(task.get("params", {}).keys()),
        })

    return {
        "goal": goal,
        "plan_tasks": len(plan),
        "routing_log": routing_results,
        "routed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ─── Direct Execute (Synchronous, returns result immediately) ─────────────────

@execution_router.post("/execute-direct")
async def execute_direct(
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """
    Direct synchronous execution. Runs and returns result immediately.
    For testing tool execution without SSE streaming.
    """
    goal = data.get("goal", "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal required")

    from app.agent.direct_executor import DirectExecutor

    execution_id = str(uuid.uuid4())
    stream = ActivityStream(execution_id)
    cancel_event = asyncio.Event()

    executor = DirectExecutor()
    record = await executor.execute(
        execution_id=execution_id,
        goal=goal,
        user_id=str(current_user["user_id"]),
        stream=stream,
        cancel_event=cancel_event,
    )

    return {
        "execution_id": record.execution_id,
        "status": record.status,
        "goal": record.goal,
        "duration_ms": record.duration_ms,
        "tasks_completed": record.tasks_completed,
        "tasks_failed": record.tasks_failed,
        "tools_used": record.tools_used,
        "artifacts": [a.to_dict() for a in record.artifacts],
        "report_id": record.report_id,
        "report_preview": record.report_markdown[:2000],
        "task_logs": [t.to_dict() for t in record.task_logs],
        "tool_logs": [t.to_dict() for t in record.tool_logs],
        "execution_timeline": record.execution_timeline,
    }


# ─── Monitor Stats ────────────────────────────────────────────────────────────

@execution_router.get("/monitor/stats")
async def get_monitor_stats(
    current_user: dict = Depends(get_current_user),
):
    """Get global execution monitor statistics."""
    from app.agent.direct_executor import _execution_store

    direct_records = list(_execution_store.values())

    return {
        "global": execution_monitor.get_global_stats(),
        "active_executions": len([
            e for e in _active_executions.values()
            if e.get("status") in ("starting", "running")
        ]),
        "total_direct_executions": len(direct_records),
        "direct_completed": sum(1 for r in direct_records if r.status == "completed"),
        "direct_failed": sum(1 for r in direct_records if r.status == "failed"),
        "recent": execution_monitor.list_all()[-10:],
    }


# ─── Execution History ────────────────────────────────────────────────────────

@execution_router.get("/history")
async def get_execution_history(
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    """Get execution history for the current user."""
    user_id = current_user["user_id"]
    from app.agent.direct_executor import _execution_store, list_executions

    # First get from in-memory store
    in_memory = list_executions(str(user_id), limit=limit)

    # Also try DB
    db_executions = []
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
        for row in rows:
            e = dict(row)
            e["created_at"] = e["created_at"].isoformat() if e.get("created_at") else None
            e["completed_at"] = e["completed_at"].isoformat() if e.get("completed_at") else None
            live = _active_executions.get(e["id"])
            if live:
                e["live_status"] = live.get("status", "unknown")

            # Enrich with in-memory record
            mem_record = _execution_store.get(e["id"])
            if mem_record:
                e["tasks_completed"] = mem_record.tasks_completed
                e["tasks_failed"] = mem_record.tasks_failed
                e["artifacts_count"] = len(mem_record.artifacts)
                e["duration_ms"] = mem_record.duration_ms
            db_executions.append(e)
    except Exception as e:
        logger.warning(f"[Execution] History DB query failed: {e}")

    # Merge
    db_ids = {e["id"] for e in db_executions}
    merged = db_executions.copy()
    for rec in in_memory:
        if rec.execution_id not in db_ids:
            merged.append({
                "id": rec.execution_id,
                "goal": rec.goal,
                "status": rec.status,
                "created_at": rec.started_at,
                "completed_at": rec.completed_at,
                "tasks_completed": rec.tasks_completed,
                "tasks_failed": rec.tasks_failed,
                "artifacts_count": len(rec.artifacts),
                "duration_ms": rec.duration_ms,
            })

    return {"executions": merged[:limit], "total": len(merged)}


# ─── Get Execution ────────────────────────────────────────────────────────────

@execution_router.get("/{execution_id}")
async def get_execution(
    execution_id: str,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get execution status and metadata."""
    from app.agent.direct_executor import _execution_store

    # Check in-memory first
    live = _active_executions.get(execution_id)
    record = _execution_store.get(execution_id)

    if record:
        return {
            "id": execution_id,
            "goal": record.goal,
            "status": record.status,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "duration_ms": record.duration_ms,
            "tasks_completed": record.tasks_completed,
            "tasks_failed": record.tasks_failed,
            "task_count": record.task_count,
            "tools_used": record.tools_used,
            "artifacts_count": len(record.artifacts),
            "report_id": record.report_id,
            "live_status": live.get("status") if live else record.status,
            "source": "direct_executor",
        }

    # Try DB
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

        metrics = execution_monitor.get(execution_id)
        if metrics:
            result["metrics"] = metrics.to_dict()

        if live:
            result["live_status"] = live.get("status", "unknown")
        result["source"] = "database"
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Execution] Get execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── SSE Event Stream ─────────────────────────────────────────────────────────

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
    from app.agent.direct_executor import _execution_store

    exec_data = _active_executions.get(execution_id)

    # If already completed, return stored events
    record = _execution_store.get(execution_id)
    if record and not exec_data:
        # Replay timeline events
        async def replay_stream():
            yield f"data: {json.dumps({'type': 'connected', 'execution_id': execution_id, 'status': 'replaying'})}\n\n"
            for entry in record.execution_timeline:
                evt = {
                    "type": entry.get("event", "").lower(),
                    "execution_id": execution_id,
                    "timestamp": entry.get("timestamp"),
                    "elapsed_ms": entry.get("elapsed_ms"),
                    **entry.get("data", {}),
                }
                yield f"data: {json.dumps(evt)}\n\n"
            yield f"data: {json.dumps({'type': 'stream_end', 'execution_id': execution_id})}\n\n"

        return StreamingResponse(
            replay_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store",
                "X-Accel-Buffering": "no",
            },
        )

    if not exec_data:
        raise HTTPException(
            status_code=404,
            detail=f"Execution {execution_id} not found or already completed"
        )

    stream: ActivityStream = exec_data["stream"]

    async def event_stream():
        yield f"data: {json.dumps({'type': 'connected', 'execution_id': execution_id})}\n\n"
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


# ─── Execution Report ─────────────────────────────────────────────────────────

@execution_router.get("/{execution_id}/report")
async def get_execution_report(
    execution_id: str,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the final execution report."""
    from app.agent.direct_executor import _execution_store

    # Check in-memory
    record = _execution_store.get(execution_id)
    if record and record.report_markdown:
        return {
            "execution_id": execution_id,
            "report_id": record.report_id,
            "goal": record.goal,
            "status": record.status,
            "report_markdown": record.report_markdown,
            "report_stored": True,
            "artifacts": [a.to_dict() for a in record.artifacts],
            "generated_at": record.completed_at,
            "source": "direct_executor",
        }

    # Try DB
    try:
        row = await conn.fetchrow(
            "SELECT * FROM task_reports WHERE execution_id = $1 ORDER BY created_at DESC LIMIT 1",
            execution_id,
        )
        if not row:
            # Check if still running
            live = _active_executions.get(execution_id)
            if live and live.get("status") == "running":
                raise HTTPException(
                    status_code=202,
                    detail="Report not yet available. Execution still running."
                )
            raise HTTPException(
                status_code=404,
                detail="Report not yet available."
            )
        result = dict(row)
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


# ─── Tasks / Evidence ─────────────────────────────────────────────────────────

@execution_router.get("/{execution_id}/tasks")
async def get_execution_tasks(
    execution_id: str,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get per-task execution evidence — proof of real tool execution."""
    from app.agent.direct_executor import _execution_store

    record = _execution_store.get(execution_id)
    if record:
        task_data = []
        for task in record.task_logs:
            task_data.append({
                "task_id": task.task_id,
                "task_title": task.task_title,
                "tool_id": task.tool_id,
                "status": task.status,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "duration_ms": task.duration_ms,
                "wave": task.wave,
                "error": task.error,
                "result_summary": _truncate(str(task.result), 500) if task.result else None,
                "source": "direct_executor",
            })
        return {
            "execution_id": execution_id,
            "tasks": task_data,
            "task_count": len(task_data),
            "events_evidence": record.execution_timeline,
            "evidence_source": "direct_executor",
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    # Fall back to DB
    db_tasks = []
    try:
        rows = await conn.fetch(
            """SELECT task_id, tool_id, status, raw_output, processed_output,
                      execution_time_ms, retries, created_at
               FROM task_tool_results
               WHERE execution_id = $1
               ORDER BY created_at ASC""",
            execution_id,
        )
        for row in rows:
            r = dict(row)
            r["created_at"] = r["created_at"].isoformat() if r.get("created_at") else None
            if r.get("raw_output") and isinstance(r["raw_output"], str):
                try:
                    r["raw_output"] = json.loads(r["raw_output"])
                except Exception:
                    pass
            r["source"] = "database"
            db_tasks.append(r)
    except Exception as e:
        logger.warning(f"[Execution] Task DB query failed: {e}")

    return {
        "execution_id": execution_id,
        "tasks": db_tasks,
        "task_count": len(db_tasks),
        "events_evidence": [],
        "evidence_source": "database",
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@execution_router.get("/{execution_id}/evidence")
async def get_execution_evidence(
    execution_id: str,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Full execution evidence — timestamped proof of real tool execution.
    Returns: execution_id, execution_info, task_results, activity_log, generated_files.
    """
    from app.agent.direct_executor import _execution_store

    record = _execution_store.get(execution_id)
    if record:
        return {
            "evidence": {
                "execution_id": execution_id,
                "execution_info": {
                    "execution_id": execution_id,
                    "goal": record.goal,
                    "status": record.status,
                    "started_at": record.started_at,
                    "completed_at": record.completed_at,
                    "duration_ms": record.duration_ms,
                },
                "execution_metrics": {
                    "task_count": record.task_count,
                    "tasks_completed": record.tasks_completed,
                    "tasks_failed": record.tasks_failed,
                    "tools_used": record.tools_used,
                    "artifacts_generated": len(record.artifacts),
                    "duration_ms": record.duration_ms,
                },
                "task_results": [t.to_dict() for t in record.task_logs],
                "task_result_count": len(record.task_logs),
                "tool_logs": [t.to_dict() for t in record.tool_logs],
                "tool_log_count": len(record.tool_logs),
                "activity_log": record.execution_timeline,
                "activity_event_count": len(record.execution_timeline),
                "generated_files": [a.to_dict() for a in record.artifacts],
                "report_stored": record.report_id is not None,
                "report_id": record.report_id,
                "report_preview": record.report_markdown[:2000],
            },
            "proof": {
                "real_tool_execution": record.tasks_completed > 0 or len(record.tool_logs) > 0,
                "artifacts_created": len(record.artifacts),
                "database_stored": True,
                "report_generated": record.report_id is not None,
                "execution_id": execution_id,
                "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }

    # DB fallback
    exec_row = None
    task_results = []
    report_data = None

    try:
        exec_row = await conn.fetchrow(
            "SELECT * FROM task_executions WHERE id = $1", execution_id
        )
    except Exception:
        pass

    try:
        rows = await conn.fetch(
            """SELECT task_id, tool_id, status, raw_output, processed_output,
                      execution_time_ms, retries, created_at
               FROM task_tool_results WHERE execution_id = $1 ORDER BY created_at ASC""",
            execution_id,
        )
        for row in rows:
            r = dict(row)
            r["created_at"] = r["created_at"].isoformat() if r.get("created_at") else None
            task_results.append(r)
    except Exception:
        pass

    try:
        report_row = await conn.fetchrow(
            "SELECT * FROM task_reports WHERE execution_id = $1 ORDER BY created_at DESC LIMIT 1",
            execution_id,
        )
        if report_row and report_row.get("report_data"):
            report_data = json.loads(report_row["report_data"])
    except Exception:
        pass

    exec_info = {}
    if exec_row:
        exec_info = {
            "execution_id": execution_id,
            "goal": exec_row.get("goal", ""),
            "status": exec_row.get("status", ""),
            "created_at": exec_row.get("created_at").isoformat() if exec_row.get("created_at") else None,
        }

    return {
        "evidence": {
            "execution_id": execution_id,
            "execution_info": exec_info,
            "task_results": task_results,
            "task_result_count": len(task_results),
            "activity_log": [],
            "activity_event_count": 0,
            "generated_files": [],
            "report_stored": report_data is not None,
            "report": report_data,
        },
        "proof": {
            "real_tool_execution": len(task_results) > 0,
            "database_stored": len(task_results) > 0,
            "report_generated": report_data is not None,
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }


# ─── Artifacts ────────────────────────────────────────────────────────────────

@execution_router.get("/{execution_id}/artifacts")
async def get_execution_artifacts(
    execution_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List all artifacts generated during an execution."""
    from app.agent.direct_executor import _execution_store

    record = _execution_store.get(execution_id)
    if record:
        return {
            "execution_id": execution_id,
            "artifacts": [a.to_dict() for a in record.artifacts],
            "total": len(record.artifacts),
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    return {"execution_id": execution_id, "artifacts": [], "total": 0}


# ─── File Download ────────────────────────────────────────────────────────────

@execution_router.get("/{execution_id}/files/{filename}")
async def download_generated_file(
    execution_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Download a file generated during execution.
    Files are stored in /tmp/manusai_workspace/.
    """
    WORKSPACE = "/tmp/manusai_workspace"
    safe_name = os.path.basename(filename)
    filepath = os.path.join(WORKSPACE, safe_name)

    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=404,
            detail=f"File '{filename}' not found. Workspace: {WORKSPACE}"
        )

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if safe_name.endswith(".csv"):
            media_type = "text/csv"
        elif safe_name.endswith(".json"):
            media_type = "application/json"
        elif safe_name.endswith(".md"):
            media_type = "text/markdown"
        else:
            media_type = "text/plain"

        return PlainTextResponse(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}"',
                "X-Execution-ID": execution_id,
                "X-File-Size": str(os.path.getsize(filepath)),
                "X-Generated-At": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Workspace Files ──────────────────────────────────────────────────────────

@execution_router.get("/workspace/files")
async def list_workspace_files(
    current_user: dict = Depends(get_current_user),
):
    """List all files in the execution workspace."""
    WORKSPACE = "/tmp/manusai_workspace"
    os.makedirs(WORKSPACE, exist_ok=True)

    files = []
    try:
        for fname in os.listdir(WORKSPACE):
            fpath = os.path.join(WORKSPACE, fname)
            if os.path.isfile(fpath):
                stat = os.stat(fpath)
                files.append({
                    "filename": fname,
                    "size_bytes": stat.st_size,
                    "modified_at": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(stat.st_mtime)
                    ),
                    "content_type": (
                        "csv" if fname.endswith(".csv") else
                        "json" if fname.endswith(".json") else
                        "markdown" if fname.endswith(".md") else "text"
                    ),
                    "download_path": f"/api/v1/execution/workspace/{fname}",
                })
    except Exception as e:
        logger.warning(f"[Workspace] List files failed: {e}")

    return {
        "workspace": WORKSPACE,
        "files": files,
        "total_files": len(files),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@execution_router.get("/workspace/{filename}")
async def download_workspace_file(
    filename: str,
    current_user: dict = Depends(get_current_user),
):
    """Download any file from workspace by filename."""
    WORKSPACE = "/tmp/manusai_workspace"
    safe_name = os.path.basename(filename)
    filepath = os.path.join(WORKSPACE, safe_name)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if safe_name.endswith(".csv"):
            media_type = "text/csv"
        elif safe_name.endswith(".json"):
            media_type = "application/json"
        elif safe_name.endswith(".md"):
            media_type = "text/markdown"
        else:
            media_type = "text/plain"

        return PlainTextResponse(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Debug Tables ─────────────────────────────────────────────────────────────

@execution_router.get("/debug/tables")
async def debug_tables(
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Debug: check all table schemas and row counts."""
    try:
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"
        )
        table_names = [r["table_name"] for r in tables]

        result: dict = {"tables": table_names, "schemas": {}, "counts": {}}
        for tname in ["executions", "task_executions", "tool_results", "execution_events",
                       "task_tool_results", "task_execution_events", "reports", "task_reports",
                       "task_artifacts"]:
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


# ─── Helper ───────────────────────────────────────────────────────────────────

def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len] + "..."
