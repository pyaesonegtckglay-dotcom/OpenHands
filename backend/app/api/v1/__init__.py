from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat, status, config, options
from app.api.v1.endpoints.settings import router as settings_router
from app.api.v1.endpoints.cognitive import cognitive_router, planner_router
from app.api.v1.endpoints.taskgraph import taskgraph_router
from app.api.v1.endpoints.stream import stream_router
from app.api.v1.endpoints.execution import execution_router
from app.api.v1.endpoints.multi_agent import router as multi_agent_router

router = APIRouter(prefix="/api/v1")

# Phase 0 routes (preserved)
router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(status.router)

# Web client config (needed by frontend)
router.include_router(config.router)

# Options endpoints for frontend compatibility
router.include_router(options.router)

# Settings endpoints for frontend compatibility
router.include_router(settings_router)

# Phase 1 routes (additive)
router.include_router(cognitive_router)
router.include_router(planner_router)

# Phase 2 routes (additive)
router.include_router(taskgraph_router)
router.include_router(stream_router)

# Phase 3 routes (additive — Tool Orchestration Engine)
router.include_router(execution_router)

# Phase 5 routes (additive — Multi-Agent Orchestration)
router.include_router(multi_agent_router)
