from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat, status
from app.api.v1.endpoints.cognitive import cognitive_router, planner_router
from app.api.v1.endpoints.taskgraph import taskgraph_router
from app.api.v1.endpoints.stream import stream_router
from app.api.v1.endpoints.execution import execution_router

router = APIRouter(prefix="/api/v1")

# Phase 0 routes (preserved)
router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(status.router)

# Phase 1 routes (additive)
router.include_router(cognitive_router)
router.include_router(planner_router)

# Phase 2 routes (additive)
router.include_router(taskgraph_router)
router.include_router(stream_router)

# Phase 3 routes (additive — Tool Orchestration Engine)
router.include_router(execution_router)
