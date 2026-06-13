"""
Tool Result Store — Phase 3
Persists tool execution results to the database.
"""
import json
import logging
import time
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ToolResultStore:
    """
    Stores tool execution results in the database.
    """

    async def save_result(
        self,
        conn,
        execution_id: str,
        task_id: str,
        tool_id: str,
        status: str,
        raw_output: Any,
        processed_output: str,
        execution_time_ms: int,
    ) -> str:
        """Save a tool result to the database."""
        result_id = str(uuid.uuid4())
        try:
            await conn.execute(
                """INSERT INTO task_tool_results
                   (id, execution_id, task_id, tool_id, status,
                    raw_output, processed_output, execution_time_ms, created_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8, NOW())
                   ON CONFLICT (id) DO NOTHING""",
                result_id, execution_id, task_id, tool_id, status,
                json.dumps(raw_output) if raw_output else "{}",
                processed_output[:10000] if processed_output else "",
                execution_time_ms,
            )
        except Exception as e:
            logger.warning(f"[ToolResultStore] Save failed: {e}")
        return result_id

    async def get_results(self, conn, execution_id: str) -> list[dict]:
        """Get all results for an execution."""
        try:
            rows = await conn.fetch(
                """SELECT * FROM task_tool_results WHERE execution_id = $1
                   ORDER BY created_at ASC""",
                execution_id,
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"[ToolResultStore] Get failed: {e}")
            return []
