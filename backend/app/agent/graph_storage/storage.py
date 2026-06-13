"""
Graph Storage — Phase 2
Persists task graphs, tasks, dependencies, and execution waves to database.

Tables (additive — Phase 0+1 tables untouched):
  task_graphs
  tasks (Phase 2 tasks, not plan_steps)
  task_dependencies
  execution_waves
"""

import json
import logging
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class GraphStorage:
    """
    Stores and retrieves task graphs from the database.
    All DB operations use asyncpg (raw SQL — no ORM).
    Phase 0+1 tables are NOT modified.
    """

    async def save_graph(
        self,
        conn,
        graph_id: str,
        plan_id: str,
        goal: str,
        validation: dict,
    ) -> str:
        """Save task graph metadata."""
        await conn.execute("""
            INSERT INTO task_graphs (id, plan_id, goal, validation_result, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET
                goal = EXCLUDED.goal,
                validation_result = EXCLUDED.validation_result
        """, graph_id, plan_id, goal, json.dumps(validation))
        logger.info(f"Graph {graph_id} saved")
        return graph_id

    async def save_tasks(self, conn, graph_id: str, tasks: list[dict]) -> None:
        """Save all atomic tasks for a graph."""
        for task in tasks:
            await conn.execute("""
                INSERT INTO graph_tasks (
                    id, graph_id, parent_id, title, description,
                    expected_output, complexity, duration,
                    parallelizable, is_blocking, status,
                    task_order, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,NOW())
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    status = EXCLUDED.status
            """,
            task["id"], graph_id,
            task.get("parent_task"),
            task["title"],
            task.get("description", ""),
            task.get("expected_output", ""),
            task.get("estimated_complexity", "medium"),
            task.get("estimated_duration", ""),
            bool(task.get("parallelizable", True)),
            bool(task.get("is_blocking", False)),
            task.get("status", "PLANNED"),
            task.get("order", 0),
            )
        logger.info(f"Saved {len(tasks)} tasks for graph {graph_id}")

    async def save_dependencies(self, conn, graph_id: str, dependencies: list[dict]) -> None:
        """Save task dependencies."""
        for dep in dependencies:
            await conn.execute("""
                INSERT INTO task_dependencies (id, graph_id, source_task, target_task, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (id) DO NOTHING
            """,
            dep["id"], graph_id,
            dep["source_task_id"],
            dep["target_task_id"],
            )
        logger.info(f"Saved {len(dependencies)} dependencies for graph {graph_id}")

    async def save_execution_waves(self, conn, graph_id: str, waves: list[dict]) -> None:
        """Save execution waves."""
        for wave in waves:
            await conn.execute("""
                INSERT INTO execution_waves (id, graph_id, wave_number, task_ids, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (id) DO UPDATE SET task_ids = EXCLUDED.task_ids
            """,
            str(uuid.uuid4()), graph_id,
            wave["wave_number"],
            json.dumps(wave["task_ids"]),
            )
        logger.info(f"Saved {len(waves)} waves for graph {graph_id}")

    async def get_graph(self, conn, graph_id: str) -> Optional[dict]:
        """Get full graph with tasks, dependencies, and waves."""
        row = await conn.fetchrow(
            "SELECT id, plan_id, goal, validation_result, created_at FROM task_graphs WHERE id = $1",
            graph_id
        )
        if not row:
            return None

        tasks = await conn.fetch(
            """SELECT id, parent_id, title, description, expected_output,
                      complexity, duration, parallelizable, is_blocking,
                      status, task_order
               FROM graph_tasks WHERE graph_id = $1 ORDER BY task_order""",
            graph_id
        )

        deps = await conn.fetch(
            "SELECT id, source_task, target_task FROM task_dependencies WHERE graph_id = $1",
            graph_id
        )

        waves = await conn.fetch(
            "SELECT wave_number, task_ids FROM execution_waves WHERE graph_id = $1 ORDER BY wave_number",
            graph_id
        )

        return {
            "graph_id": str(row["id"]),
            "plan_id": str(row["plan_id"]) if row["plan_id"] else None,
            "goal": row["goal"],
            "validation": json.loads(row["validation_result"]) if row["validation_result"] else {},
            "created_at": str(row["created_at"]),
            "tasks": [
                {
                    "id": str(t["id"]),
                    "parent_id": str(t["parent_id"]) if t["parent_id"] else None,
                    "title": t["title"],
                    "description": t["description"],
                    "expected_output": t["expected_output"],
                    "complexity": t["complexity"],
                    "duration": t["duration"],
                    "parallelizable": t["parallelizable"],
                    "is_blocking": t["is_blocking"],
                    "status": t["status"],
                    "order": t["task_order"],
                }
                for t in tasks
            ],
            "dependencies": [
                {
                    "id": str(d["id"]),
                    "source_task": str(d["source_task"]),
                    "target_task": str(d["target_task"]),
                }
                for d in deps
            ],
            "waves": [
                {
                    "wave_number": w["wave_number"],
                    "task_ids": json.loads(w["task_ids"]) if isinstance(w["task_ids"], str) else w["task_ids"],
                }
                for w in waves
            ],
        }

    async def list_graphs(self, conn, limit: int = 20, offset: int = 0) -> list[dict]:
        """List all task graphs."""
        rows = await conn.fetch(
            """SELECT g.id, g.plan_id, g.goal, g.created_at,
                      COUNT(t.id) as task_count
               FROM task_graphs g
               LEFT JOIN graph_tasks t ON t.graph_id = g.id
               GROUP BY g.id, g.plan_id, g.goal, g.created_at
               ORDER BY g.created_at DESC LIMIT $1 OFFSET $2""",
            limit, offset
        )
        return [
            {
                "graph_id": str(r["id"]),
                "plan_id": str(r["plan_id"]) if r["plan_id"] else None,
                "goal": r["goal"],
                "task_count": r["task_count"],
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]

    async def get_waves(self, conn, graph_id: str) -> list[dict]:
        """Get execution waves for a graph."""
        waves = await conn.fetch(
            """SELECT w.wave_number, w.task_ids,
                      w.created_at
               FROM execution_waves w WHERE w.graph_id = $1 ORDER BY w.wave_number""",
            graph_id
        )

        result = []
        for w in waves:
            task_ids = json.loads(w["task_ids"]) if isinstance(w["task_ids"], str) else w["task_ids"]
            # Get task details for this wave
            if task_ids:
                tasks = await conn.fetch(
                    "SELECT id, title, parallelizable, is_blocking FROM graph_tasks WHERE id = ANY($1::text[])",
                    task_ids
                )
                task_info = [
                    {
                        "id": str(t["id"]),
                        "title": t["title"],
                        "parallelizable": t["parallelizable"],
                        "is_blocking": t["is_blocking"],
                    }
                    for t in tasks
                ]
            else:
                task_info = []

            result.append({
                "wave_number": w["wave_number"],
                "task_ids": task_ids,
                "tasks": task_info,
                "can_run_parallel": len(task_ids) > 1,
            })

        return result
