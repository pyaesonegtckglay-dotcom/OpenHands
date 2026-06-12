"""
Task Graph API Endpoints — Phase 2
POST /api/v1/taskgraph/create
GET  /api/v1/taskgraph/{graph_id}
GET  /api/v1/taskgraph/{graph_id}/waves
GET  /api/v1/taskgraph/list

Converts validated Phase 1 plans into structured task graphs.
NO EXECUTION — planning only.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from asyncpg import Connection

from app.database.connection import get_db
from app.core.security import get_current_user, get_optional_user
from app.agent.task_graph import TaskGraphEngine

logger = logging.getLogger(__name__)

taskgraph_router = APIRouter(prefix="/taskgraph", tags=["Task Graph — Phase 2"])

# Singleton engine
_engine = TaskGraphEngine()


# ─── Request / Response Models ───────────────────────────────────────────────

class CreateGraphRequest(BaseModel):
    plan_id: str = Field(..., description="Phase 1 plan ID to convert into task graph")


class CreateGraphResponse(BaseModel):
    graph_id: str
    plan_id: str
    goal: str
    total_tasks: int
    total_waves: int
    max_parallel: int
    estimated_duration: str
    is_valid: bool
    validation_errors: List[str]
    validation_warnings: List[str]
    regeneration_count: int


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    expected_output: str
    estimated_complexity: str
    estimated_duration: str
    parent_task: Optional[str]
    child_tasks: List[str]
    dependencies: List[str]
    status: str
    order: int
    parallelizable: bool
    is_blocking: bool


class DependencyResponse(BaseModel):
    id: str
    source_task_id: str
    target_task_id: str


class ExecutionWaveResponse(BaseModel):
    wave_number: int
    task_ids: List[str]
    task_titles: List[str]
    can_run_parallel: bool
    all_blocking: bool


class GraphDetailResponse(BaseModel):
    graph_id: str
    plan_id: Optional[str]
    goal: str
    tasks: List[TaskResponse]
    dependencies: List[DependencyResponse]
    waves: List[ExecutionWaveResponse]
    stats: dict
    validation: dict
    created_at: Optional[str] = None


class GraphListItem(BaseModel):
    graph_id: str
    plan_id: Optional[str]
    goal: str
    task_count: int
    created_at: str


class GraphListResponse(BaseModel):
    graphs: List[GraphListItem]
    total: int


class WaveDetailResponse(BaseModel):
    wave_number: int
    task_ids: List[str]
    tasks: List[dict]
    can_run_parallel: bool


# ─── Endpoints ───────────────────────────────────────────────────────────────

@taskgraph_router.post("/create", response_model=CreateGraphResponse)
async def create_task_graph(
    data: CreateGraphRequest,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a task graph from a validated Phase 1 plan.

    Transforms plan steps into atomic tasks with:
    - Parent-child hierarchy
    - Dependency relationships
    - Parallel execution markers
    - Blocking task markers
    - Execution waves

    Input:  { "plan_id": "uuid" }
    Output: { "graph_id": "uuid", "total_tasks": N, ... }
    """
    logger.info(f"[API] Creating task graph for plan_id={data.plan_id}")

    result = await _engine.create_graph(
        plan_id=data.plan_id,
        conn=conn,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in (result.error or "").lower()
            else status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.error or "Task graph creation failed",
        )

    graph = result.graph
    return CreateGraphResponse(
        graph_id=graph.graph_id,
        plan_id=graph.plan_id,
        goal=graph.goal,
        total_tasks=len(graph.tasks),
        total_waves=graph.execution_plan.total_waves,
        max_parallel=graph.execution_plan.max_parallel,
        estimated_duration=graph.execution_plan.estimated_duration,
        is_valid=graph.validation.is_valid,
        validation_errors=graph.validation.errors,
        validation_warnings=graph.validation.warnings,
        regeneration_count=graph.regeneration_count,
    )


@taskgraph_router.get("/list", response_model=GraphListResponse)
async def list_task_graphs(
    limit: int = 20,
    offset: int = 0,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all task graphs."""
    try:
        graphs = await _engine.list_graphs(conn, limit=limit, offset=offset)
        return GraphListResponse(
            graphs=[GraphListItem(**g) for g in graphs],
            total=len(graphs),
        )
    except Exception as e:
        logger.error(f"Failed to list graphs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task graphs",
        )


@taskgraph_router.get("/{graph_id}/waves", response_model=List[WaveDetailResponse])
async def get_execution_waves(
    graph_id: str,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get execution waves for a task graph.

    Returns ordered waves showing what can run simultaneously
    and what must wait.
    """
    try:
        waves = await _engine.get_waves(graph_id, conn)
        if not waves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task graph '{graph_id}' not found or has no waves",
            )
        return [WaveDetailResponse(**w) for w in waves]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get waves for {graph_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve execution waves",
        )


@taskgraph_router.get("/{graph_id}", response_model=GraphDetailResponse)
async def get_task_graph(
    graph_id: str,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get full task graph with all tasks, dependencies, and waves.
    """
    try:
        graph = await _engine.get_graph(graph_id, conn)
        if not graph:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task graph '{graph_id}' not found",
            )

        # Build execution waves with task titles
        task_title_map = {t["id"]: t["title"] for t in graph.get("tasks", [])}
        formatted_waves = []
        for w in graph.get("waves", []):
            task_ids = w.get("task_ids", [])
            task_titles = [task_title_map.get(tid, tid) for tid in task_ids]
            all_tasks = graph.get("tasks", [])
            blocking = all(
                next((t["is_blocking"] for t in all_tasks if t["id"] == tid), False)
                for tid in task_ids
            ) if task_ids else False
            formatted_waves.append(ExecutionWaveResponse(
                wave_number=w["wave_number"],
                task_ids=task_ids,
                task_titles=task_titles,
                can_run_parallel=len(task_ids) > 1,
                all_blocking=blocking,
            ))

        tasks_resp = []
        for t in graph.get("tasks", []):
            # Find dependencies for this task from deps
            task_deps = [
                d["source_task"] for d in graph.get("dependencies", [])
                if d["target_task"] == t["id"]
            ]
            tasks_resp.append(TaskResponse(
                id=t["id"],
                title=t["title"],
                description=t.get("description", ""),
                expected_output=t.get("expected_output", ""),
                estimated_complexity=t.get("complexity", "medium"),
                estimated_duration=t.get("duration", ""),
                parent_task=t.get("parent_id"),
                child_tasks=[
                    d["target_task"] for d in graph.get("dependencies", [])
                    if d["source_task"] == t["id"]
                ],
                dependencies=task_deps,
                status=t.get("status", "PLANNED"),
                order=t.get("order", 0),
                parallelizable=bool(t.get("parallelizable", True)),
                is_blocking=bool(t.get("is_blocking", False)),
            ))

        deps_resp = [
            DependencyResponse(
                id=d["id"],
                source_task_id=d["source_task"],
                target_task_id=d["target_task"],
            )
            for d in graph.get("dependencies", [])
        ]

        # Compute stats
        tasks_data = graph.get("tasks", [])
        stats = {
            "total_tasks": len(tasks_data),
            "total_dependencies": len(graph.get("dependencies", [])),
            "total_waves": len(graph.get("waves", [])),
            "blocking_tasks": sum(1 for t in tasks_data if t.get("is_blocking")),
            "parallel_tasks": sum(1 for t in tasks_data if t.get("parallelizable")),
        }

        return GraphDetailResponse(
            graph_id=graph["graph_id"],
            plan_id=graph.get("plan_id"),
            goal=graph["goal"],
            tasks=tasks_resp,
            dependencies=deps_resp,
            waves=formatted_waves,
            stats=stats,
            validation=graph.get("validation", {}),
            created_at=graph.get("created_at"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get graph {graph_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task graph",
        )
