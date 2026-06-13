"""
Supabase PostgreSQL database connection layer.
Uses raw asyncpg connection pool with statement_cache_size=0
for PgBouncer transaction mode compatibility.
"""
import logging
import asyncpg
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


def _get_raw_dsn(url: str) -> str:
    """Strip SQLAlchemy dialect prefix."""
    for prefix in ("postgresql+asyncpg://",):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = _get_raw_dsn(settings.DATABASE_URL)
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=1,
            max_size=10,
            statement_cache_size=0,  # Required for PgBouncer transaction mode
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_db():
    """Dependency: yields an asyncpg connection from the pool."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def check_db_health() -> dict:
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "connected", "service": "supabase_postgresql"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "disconnected", "service": "supabase_postgresql", "error": str(e)}


async def init_db():
    """Create/migrate tables."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Conversations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) DEFAULT 'New Conversation',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Check conversations.id type — if varchar, drop and recreate all
        conv_type = await conn.fetchval("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'conversations' AND column_name = 'id'
        """)
        if conv_type and conv_type.lower() in ('character varying', 'text', 'varchar'):
            logger.info("Migrating tables from VARCHAR to UUID schema...")
            await conn.execute("DROP TABLE IF EXISTS messages CASCADE")
            await conn.execute("DROP TABLE IF EXISTS conversations CASCADE")
            await conn.execute("DROP TABLE IF EXISTS users CASCADE")
            # Recreate all
            await conn.execute("""
                CREATE TABLE users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(255) DEFAULT 'New Conversation',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

        # Messages table — drop and recreate if schema mismatch
        col_check = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'messages' AND column_name = 'role'
        """)
        if col_check == 0:
            await conn.execute("DROP TABLE IF EXISTS messages CASCADE")
            await conn.execute("""
                CREATE TABLE messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            logger.info("Messages table created/recreated")
        else:
            logger.info("Messages table schema OK")

        # Indexes (Phase 0)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_convs_user_id ON conversations(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_msgs_conv_id ON messages(conversation_id)")

        # Phase 1 — Cognitive Layer: plans + plan_steps tables
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID,
                goal TEXT NOT NULL,
                intent VARCHAR(50),
                task_type VARCHAR(50),
                complexity INTEGER DEFAULT 5,
                planning_required BOOLEAN DEFAULT TRUE,
                plan_depth VARCHAR(20),
                provider_used VARCHAR(50),
                model_used VARCHAR(100),
                status VARCHAR(20) DEFAULT 'created',
                error_message TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS plan_steps (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
                step_order INTEGER NOT NULL,
                step_id VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                expected_output TEXT NOT NULL,
                dependencies JSONB DEFAULT '[]'::jsonb,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_user_id ON plans(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_plan_steps_plan_id ON plan_steps(plan_id)")
        logger.info("Phase 1 plan tables initialized")

        # ── Phase 2 — Task Graph Engine ────────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_graphs (
                id TEXT PRIMARY KEY,
                plan_id TEXT,
                goal TEXT NOT NULL,
                validation_result JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS graph_tasks (
                id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL REFERENCES task_graphs(id) ON DELETE CASCADE,
                parent_id TEXT,
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                expected_output TEXT NOT NULL DEFAULT '',
                complexity VARCHAR(20) DEFAULT 'medium',
                duration VARCHAR(100) DEFAULT '',
                parallelizable BOOLEAN DEFAULT TRUE,
                is_blocking BOOLEAN DEFAULT FALSE,
                status VARCHAR(20) DEFAULT 'PLANNED',
                task_order INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_dependencies (
                id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL REFERENCES task_graphs(id) ON DELETE CASCADE,
                source_task TEXT NOT NULL,
                target_task TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_waves (
                id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL REFERENCES task_graphs(id) ON DELETE CASCADE,
                wave_number INTEGER NOT NULL,
                task_ids JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_task_graphs_plan_id ON task_graphs(plan_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_tasks_graph_id ON graph_tasks(graph_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_task_deps_graph_id ON task_dependencies(graph_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_exec_waves_graph_id ON execution_waves(graph_id)")
        logger.info("Phase 2 task graph tables initialized")

        # ── Phase 3 — Tool Orchestration Engine ───────────────────────────────
        # Executions table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_executions (
                id TEXT PRIMARY KEY,
                user_id UUID,
                goal TEXT NOT NULL,
                status VARCHAR(30) DEFAULT 'STARTED',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                completed_at TIMESTAMPTZ
            )
        """)

        # Migration: add missing columns to executions table (idempotent)
        try:
            await conn.execute("ALTER TABLE task_executions ADD COLUMN IF NOT EXISTS user_id UUID")
            await conn.execute("ALTER TABLE task_executions ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ")
            await conn.execute("ALTER TABLE task_executions ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'STARTED'")
        except Exception as _mig_err:
            logger.debug(f"executions migration (expected if columns exist): {_mig_err}")
        logger.info("Phase 3 executions table ready")

        # Tool results table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_tool_results (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                tool_id VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL,
                raw_output TEXT DEFAULT '{}',
                processed_output TEXT DEFAULT '',
                execution_time_ms INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Execution events table (persistent event log)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_execution_events (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                event_type VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                data TEXT DEFAULT '{}',
                level VARCHAR(20) DEFAULT 'info',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Reports table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_reports (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                goal TEXT NOT NULL,
                report_markdown TEXT NOT NULL DEFAULT '',
                report_data TEXT DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Artifacts table (Phase 3 — file artifact tracking)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS task_artifacts (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                filename VARCHAR(500) NOT NULL,
                content_type VARCHAR(100) DEFAULT 'text/plain',
                size_bytes INTEGER DEFAULT 0,
                download_url TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Migration: ensure task_reports has all required columns
        try:
            await conn.execute("ALTER TABLE task_reports ADD COLUMN IF NOT EXISTS goal TEXT NOT NULL DEFAULT ''")
            await conn.execute("ALTER TABLE task_reports ADD COLUMN IF NOT EXISTS report_markdown TEXT NOT NULL DEFAULT ''")
            await conn.execute("ALTER TABLE task_reports ADD COLUMN IF NOT EXISTS report_data TEXT DEFAULT '{}'")
        except Exception as _mig_err:
            logger.debug(f"task_reports migration: {_mig_err}")

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_task_executions_user_id ON task_executions(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_task_tool_results_exec_id ON task_tool_results(execution_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_task_exec_events_exec_id ON task_execution_events(execution_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_task_reports_exec_id ON task_reports(execution_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_task_artifacts_exec_id ON task_artifacts(execution_id)")
        logger.info("Phase 3 execution tables initialized")

    logger.info("Database tables initialized successfully")
