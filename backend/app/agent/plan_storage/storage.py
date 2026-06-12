"""
Plan Storage
Stores and retrieves plans from the database.
Tables: plans, plan_steps
"""

import json
import uuid
import logging
from typing import Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlanStorage:
    """
    Handles persistence of plans and plan steps.
    Uses asyncpg connection (raw SQL, no ORM).
    """

    async def init_tables(self, conn) -> None:
        """Create plans and plan_steps tables if they don't exist."""
        # plans table
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

        # plan_steps table
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

        # Indexes
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_plans_user_id ON plans(user_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_plan_steps_plan_id ON plan_steps(plan_id)"
        )
        logger.info("Plan tables initialized")

    async def save_plan(
        self,
        conn,
        plan_id: str,
        goal: str,
        intent: str,
        task_type: str,
        complexity: int,
        planning_required: bool,
        plan_depth: str,
        provider_used: str = "",
        model_used: str = "",
        error_message: str | None = None,
        user_id: str | None = None,
    ) -> str:
        """Save a plan record. Returns the plan ID."""
        await conn.execute(
            """
            INSERT INTO plans (
                id, user_id, goal, intent, task_type, complexity,
                planning_required, plan_depth, provider_used, model_used,
                error_message
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (id) DO UPDATE SET
                goal = EXCLUDED.goal,
                intent = EXCLUDED.intent,
                task_type = EXCLUDED.task_type,
                complexity = EXCLUDED.complexity,
                planning_required = EXCLUDED.planning_required,
                plan_depth = EXCLUDED.plan_depth,
                provider_used = EXCLUDED.provider_used,
                model_used = EXCLUDED.model_used,
                error_message = EXCLUDED.error_message
            """,
            uuid.UUID(plan_id),
            uuid.UUID(user_id) if user_id else None,
            goal,
            intent,
            task_type,
            complexity,
            planning_required,
            plan_depth,
            provider_used,
            model_used,
            error_message,
        )
        return plan_id

    async def save_plan_steps(self, conn, plan_id: str, steps: list[dict]) -> None:
        """Save plan steps for a given plan ID."""
        # Delete existing steps for this plan (idempotent)
        await conn.execute(
            "DELETE FROM plan_steps WHERE plan_id = $1",
            uuid.UUID(plan_id),
        )

        for order, step in enumerate(steps):
            await conn.execute(
                """
                INSERT INTO plan_steps (
                    plan_id, step_order, step_id, title,
                    description, expected_output, dependencies, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                uuid.UUID(plan_id),
                order,
                step.get("id", f"step_{order + 1}"),
                step.get("title", ""),
                step.get("description", ""),
                step.get("expected_output", ""),
                json.dumps(step.get("dependencies", [])),
                step.get("status", "pending"),
            )

    async def get_plan(self, conn, plan_id: str) -> dict | None:
        """Get a plan with all its steps."""
        plan_row = await conn.fetchrow(
            "SELECT * FROM plans WHERE id = $1",
            uuid.UUID(plan_id),
        )
        if not plan_row:
            return None

        step_rows = await conn.fetch(
            "SELECT * FROM plan_steps WHERE plan_id = $1 ORDER BY step_order",
            uuid.UUID(plan_id),
        )

        steps = []
        for row in step_rows:
            deps = row["dependencies"]
            if isinstance(deps, str):
                deps = json.loads(deps)
            steps.append({
                "id": row["step_id"],
                "title": row["title"],
                "description": row["description"],
                "expected_output": row["expected_output"],
                "dependencies": deps or [],
                "status": row["status"],
            })

        return {
            "plan_id": str(plan_row["id"]),
            "goal": plan_row["goal"],
            "intent": plan_row["intent"],
            "task_type": plan_row["task_type"],
            "complexity": plan_row["complexity"],
            "planning_required": plan_row["planning_required"],
            "plan_depth": plan_row["plan_depth"],
            "provider_used": plan_row["provider_used"],
            "model_used": plan_row["model_used"],
            "error_message": plan_row["error_message"],
            "created_at": plan_row["created_at"].isoformat() if plan_row["created_at"] else None,
            "steps": steps,
        }

    async def list_plans(
        self, conn, user_id: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        """List plans with pagination."""
        if user_id:
            rows = await conn.fetch(
                """SELECT id, goal, intent, task_type, complexity,
                          planning_required, plan_depth, provider_used,
                          status, created_at
                   FROM plans WHERE user_id = $1
                   ORDER BY created_at DESC
                   LIMIT $2 OFFSET $3""",
                uuid.UUID(user_id), limit, offset,
            )
        else:
            rows = await conn.fetch(
                """SELECT id, goal, intent, task_type, complexity,
                          planning_required, plan_depth, provider_used,
                          status, created_at
                   FROM plans
                   ORDER BY created_at DESC
                   LIMIT $1 OFFSET $2""",
                limit, offset,
            )

        return [
            {
                "plan_id": str(row["id"]),
                "goal": row["goal"],
                "intent": row["intent"],
                "task_type": row["task_type"],
                "complexity": row["complexity"],
                "planning_required": row["planning_required"],
                "plan_depth": row["plan_depth"],
                "provider_used": row["provider_used"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]
