"""
ManusAI Phase 5 - Multi-Agent Orchestration
Phase 0: Foundation Layer (preserved - OpenHands runtime, auth, chat)
Phase 1: Cognitive Layer (intent classification, goal extraction, planning)
Phase 2: Task Graph Engine (task decomposition, dependency graph, execution waves)
Phase 3: Tool Orchestration Engine (real execution, tool registry, activity stream, reports)
Phase 5: Multi-Agent Orchestration (multiple agents, teams, collaboration modes)
Infrastructure: Supabase PostgreSQL + Redis + E2B Sandbox
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_router
from app.api.v1.endpoints.options import router as options_router
from app.api.v1.endpoints.settings import router as settings_router
from app.api.v1.endpoints.conversations import router as conversations_router
from app.core.config import settings
from app.database.connection import init_db, close_pool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    logger.info("ManusAI Phase 3 (Tool Orchestration Engine) starting up...")
    try:
        await init_db()
        logger.info("✓ Database initialized (Phase 0+1+2+3 tables)")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Initialize tool registry (self-registering tools)
    try:
        import app.agent.tool_registry.tools  # noqa: F401
        from app.agent.tool_registry import tool_registry
        logger.info(f"✓ Tool Registry initialized: {len(tool_registry.list_enabled())} tools registered")
    except Exception as e:
        logger.error(f"Tool Registry initialization failed: {e}")

    yield

    logger.info("ManusAI Phase 3 shutting down...")
    from app.cache.redis_client import close_redis
    await close_redis()
    await close_pool()


app = FastAPI(
    title="ManusAI - Phase 5",
    description=(
        "ManusAI Phase 5 — Multi-Agent Orchestration. "
        "Phase 0: Foundation Layer (auth, chat, infrastructure). "
        "Phase 1: Cognitive Layer (intent classification, goal extraction, planning). "
        "Phase 2: Task Graph Engine (task decomposition, dependency graph, execution waves). "
        "Phase 3: Tool Orchestration Engine (real execution, tool registry, activity stream, reports). "
        "Phase 5: Multi-Agent Orchestration (multiple agents, teams, collaboration modes). "
        "Providers: Gemini → GitHub Models → SambaNova (fallback chain). "
        "Infrastructure: Supabase PostgreSQL + Redis + E2B Sandbox. "
        "Tools: Web Search, HTTP Request, File Reader, File Writer, Calculator, Python Executor, AI Synthesis."
    ),
    version="5.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes - include root-level routers BEFORE api_router to avoid prefix conflicts
app.include_router(options_router)  # /api/options/*
app.include_router(conversations_router)  # /api/conversations/*
app.include_router(settings_router)  # /settings/*
app.include_router(api_router)  # /api/v1/*


@app.get("/")
async def root():
    return {
        "name": "ManusAI",
        "phase": "5",
        "phase_name": "Multi-Agent Orchestration",
        "description": "Phase 0: Foundation + Phase 1: Cognitive Layer + Phase 2: Task Graph Engine + Phase 3: Tool Orchestration + Phase 5: Multi-Agent Orchestration",
        "version": "5.0.0",
        "docs": "/docs",
        "phases": {
            "0": {"name": "Foundation Layer", "status": "active", "endpoints": ["/api/v1/auth", "/api/v1/chat", "/api/v1/status"]},
            "1": {"name": "Cognitive Layer", "status": "active", "endpoints": ["/api/v1/cognitive/analyze", "/api/v1/planner/create", "/api/v1/planner/list"]},
            "2": {"name": "Task Graph Engine", "status": "active", "endpoints": ["/api/v1/taskgraph/create", "/api/v1/taskgraph/list", "/api/v1/stream/chat"]},
            "3": {"name": "Tool Orchestration Engine", "status": "active", "endpoints": [
                "/api/v1/execution/start",
                "/api/v1/execution/stop",
                "/api/v1/execution/{id}",
                "/api/v1/execution/{id}/events",
                "/api/v1/execution/{id}/report",
                "/api/v1/execution/history",
                "/api/v1/execution/tools/registry",
                "/api/v1/execution/monitor/stats",
            ]},
            "5": {"name": "Multi-Agent Orchestration", "status": "active", "endpoints": [
                "/api/v1/multi-agent/teams/create",
                "/api/v1/multi-agent/teams",
                "/api/v1/multi-agent/agents",
                "/api/v1/multi-agent/execute",
                "/api/v1/multi-agent/execute/stream",
                "/api/v1/multi-agent/executions",
                "/api/v1/multi-agent/types",
                "/api/v1/multi-agent/modes",
            ]}
        }
    }


@app.get("/ping")
async def ping():
    return {"pong": True}

