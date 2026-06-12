"""
Phase 3 — Tool Orchestration Engine
Main execution engine that ties all Phase 3 components together.

Pipeline:
  User Input
    → Intent Classifier
    → Complexity Analyzer
    → Planner Trigger
    → Plan Generator
    → Task Graph Engine
    → Execution Scheduler (with Tool Router → Tool Executor per task)
    → Result Collector
    → Report Generator
    → User (streaming events + final report)
"""
import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Optional

from app.agent.cognitive_pipeline import CognitivePipeline
from app.agent.task_graph.engine import TaskGraphEngine
from app.agent.execution_scheduler import ExecutionScheduler, ScheduledTask, TaskState
from app.agent.tool_router import ToolRouter
from app.agent.activity_stream import ActivityStream
from app.agent.report_generator import ReportGenerator, ExecutionReport
from app.agent.execution_monitor import execution_monitor
from app.agent.tool_result_store import ToolResultStore

# Import tools so they self-register
import app.agent.tool_registry.tools  # noqa: F401

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context for a single execution run."""
    execution_id: str
    goal: str
    user_id: str
    conn: Any  # database connection
    stream: ActivityStream
    plan_id: Optional[str] = None
    graph_id: Optional[str] = None
    tasks: dict = field(default_factory=dict)
    report: Optional[ExecutionReport] = None
    cancel_event: Optional[asyncio.Event] = None
    started_at: float = field(default_factory=time.time)


class ExecutionEngine:
    """
    Phase 3 Execution Engine.
    Orchestrates: Plan → Task Graph → Tool Execution → Report.
    Streams every event in real-time.
    """

    def __init__(self):
        self.cognitive_pipeline = CognitivePipeline()
        self.task_graph_engine = TaskGraphEngine()
        self.tool_router = ToolRouter()
        self.report_generator = ReportGenerator()
        self.result_store = ToolResultStore()

    async def execute(
        self,
        execution_id: str,
        goal: str,
        user_id: str,
        conn: Any,
        stream: ActivityStream,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> ExecutionReport:
        """
        Full execution pipeline.

        Args:
            execution_id: Unique execution identifier
            goal: User's goal
            user_id: User ID
            conn: Database connection
            stream: ActivityStream for real-time events
            cancel_event: asyncio.Event to stop execution

        Returns:
            ExecutionReport with all findings and results
        """
        ctx = ExecutionContext(
            execution_id=execution_id,
            goal=goal,
            user_id=user_id,
            conn=conn,
            stream=stream,
            cancel_event=cancel_event or asyncio.Event(),
        )

        try:
            # Phase 1: Intent Classification & Planning
            await stream.emit("intent_detected", {
                "execution_id": execution_id,
                "goal": goal[:100],
            })

            await stream.emit("planning_started", {
                "execution_id": execution_id,
            })

            plan_data = await self._run_cognitive_pipeline(ctx)

            if ctx.cancel_event.is_set():
                return await self._generate_partial_report(ctx)

            # Phase 2: Task Graph Creation
            await stream.emit("task_graph_created", {
                "execution_id": execution_id,
                "total_tasks": plan_data.get("task_count", 0),
            })

            tasks_by_wave = await self._build_execution_tasks(ctx, plan_data)
            total_tasks = sum(len(t) for t in tasks_by_wave.values())

            if ctx.cancel_event.is_set():
                return await self._generate_partial_report(ctx)

            # Start execution monitor
            execution_monitor.start(execution_id, goal, total_tasks)

            await stream.emit("execution_started", {
                "execution_id": execution_id,
                "total_tasks": total_tasks,
                "total_waves": len(tasks_by_wave),
            })

            # Phase 3: Schedule & Execute
            scheduler = ExecutionScheduler(
                event_callback=self._make_event_callback(stream),
            )
            scheduler.cancel_event = ctx.cancel_event

            completed_tasks = await scheduler.execute_graph(
                execution_id=execution_id,
                tasks_by_wave=tasks_by_wave,
                max_parallel=4,
            )
            ctx.tasks = completed_tasks

            # Save results to DB
            await self._persist_results(ctx, completed_tasks)

            # Update monitor
            stats = scheduler.get_stats()
            execution_monitor.finish(
                execution_id,
                completed=stats["completed"],
                failed=stats["failed"],
            )

            # Phase 4: Generate Report
            await stream.emit("report_generating", {
                "execution_id": execution_id,
            })

            report = self.report_generator.generate(
                execution_id=execution_id,
                goal=goal,
                tasks=completed_tasks,
                events=stream.get_all_events(),
                partial=ctx.cancel_event.is_set(),
            )
            ctx.report = report

            # Save report to DB
            await self._save_report(ctx, report)

            await stream.emit("report_complete", {
                "execution_id": execution_id,
                "success_rate": stats.get("completed", 0),
            }, level="success")

            return report

        except asyncio.CancelledError:
            logger.info(f"[ExecutionEngine] Execution {execution_id} cancelled")
            return await self._generate_partial_report(ctx)
        except Exception as e:
            logger.error(f"[ExecutionEngine] Execution {execution_id} failed: {e}", exc_info=True)
            await stream.emit("error", {
                "execution_id": execution_id,
                "error": str(e),
            }, level="error")
            return await self._generate_partial_report(ctx)

    async def _run_cognitive_pipeline(self, ctx: ExecutionContext) -> dict:
        """Run cognitive pipeline to get plan."""
        goal = ctx.goal
        stream = ctx.stream
        conn = ctx.conn

        try:
            result = await self.cognitive_pipeline.run_full_pipeline(goal, conn, user_id=ctx.user_id)

            if result.plan_id:
                ctx.plan_id = result.plan_id
                plan = result.plan or {}
                steps = plan.get("steps", []) if plan else []

                await stream.emit("plan_generated", {
                    "execution_id": ctx.execution_id,
                    "plan_id": result.plan_id,
                    "step_count": len(steps),
                })

                return {
                    "plan_id": result.plan_id,
                    "goal": goal,
                    "steps": steps,
                    "task_count": len(steps),
                    "intent": result.analysis.intent if result.analysis else "TASK",
                    "complexity": result.analysis.complexity if result.analysis else 5,
                }
            elif result.plan:
                # Has plan data but maybe no ID stored
                plan = result.plan
                steps = plan.get("steps", [])
                await stream.emit("plan_generated", {
                    "execution_id": ctx.execution_id,
                    "plan_id": "inline",
                    "step_count": len(steps),
                })
                return {
                    "plan_id": "inline",
                    "goal": goal,
                    "steps": steps,
                    "task_count": len(steps),
                    "intent": result.analysis.intent if result.analysis else "TASK",
                    "complexity": result.analysis.complexity if result.analysis else 5,
                }
            else:
                # No plan generated — create minimal task set
                return self._minimal_plan(goal)

        except Exception as e:
            logger.warning(f"[ExecutionEngine] Cognitive pipeline error: {e}")
            return self._minimal_plan(goal)

    def _minimal_plan(self, goal: str) -> dict:
        """Create a minimal plan when cognitive pipeline fails."""
        return {
            "plan_id": None,
            "goal": goal,
            "steps": [
                {
                    "title": f"Research: {goal[:80]}",
                    "description": f"Search for information about: {goal}",
                    "expected_output": "Key findings and information",
                },
                {
                    "title": f"Analyze findings",
                    "description": f"Analyze and synthesize research results for: {goal}",
                    "expected_output": "Comprehensive analysis and insights",
                },
            ],
            "task_count": 2,
            "intent": "TASK",
            "complexity": 5,
        }

    async def _build_execution_tasks(
        self,
        ctx: ExecutionContext,
        plan_data: dict,
    ) -> dict[int, list[ScheduledTask]]:
        """Convert plan steps into scheduled tasks with tool routing."""
        steps = plan_data.get("steps", [])
        goal = plan_data.get("goal", ctx.goal)

        if not steps:
            steps = [
                {"title": f"Execute: {goal[:80]}", "description": goal, "expected_output": "Result"},
            ]

        tasks_by_wave: dict[int, list[ScheduledTask]] = {}

        for i, step in enumerate(steps):
            title = step.get("title", f"Task {i+1}")
            description = step.get("description", "")
            expected_output = step.get("expected_output", "")
            deps = step.get("dependencies", [])

            # Determine wave from dependencies
            wave = len(deps) if deps else 0
            # Simple wave assignment: first few steps in wave 0, rest in wave 1
            if i < 2:
                wave = 0
            elif i < 5:
                wave = 1
            else:
                wave = 2

            # Route to tool
            route = self.tool_router.route(title, description, expected_output)

            # Refine params with goal context
            params = self._refine_params(route.tool_id, route.params, title, description, goal)

            task = ScheduledTask(
                id=f"task_{i+1}_{uuid.uuid4().hex[:6]}",
                title=title,
                description=description,
                expected_output=expected_output,
                tool_id=route.tool_id,
                tool_params=params,
                wave=wave,
                dependencies=[],
            )

            if wave not in tasks_by_wave:
                tasks_by_wave[wave] = []
            tasks_by_wave[wave].append(task)

            await ctx.stream.emit("tool_selected", {
                "execution_id": ctx.execution_id,
                "task_id": task.id,
                "task_title": title,
                "tool": route.tool_id,
                "confidence": route.confidence,
            })

        return tasks_by_wave

    def _refine_params(self, tool_id: str, params: dict, title: str, description: str, goal: str) -> dict:
        """Refine tool parameters with additional context."""
        if tool_id == "web_search":
            # Use title as search query if not set well
            if not params.get("query") or len(params["query"]) < 3:
                params["query"] = title
            return params

        elif tool_id == "ai_synthesis":
            params["prompt"] = f"{title}: {description}"
            params["context"] = f"Overall goal: {goal}"
            return params

        elif tool_id == "file_writer":
            # Ensure reasonable filename
            if not params.get("filename") or params["filename"] == "output.txt":
                # Generate filename from task title
                safe_name = title.lower().replace(" ", "_").replace("/", "_")[:30]
                params["filename"] = f"{safe_name}.txt"
            # Generate basic content
            params["content"] = (
                f"# {title}\n\n"
                f"Goal: {goal}\n\n"
                f"Description: {description}\n\n"
                f"Generated by ManusAI Phase 3\n"
            )
            return params

        elif tool_id == "python_executor":
            params["code"] = (
                f"# Task: {title}\n"
                f"# Goal: {goal}\n"
                f"# Description: {description}\n\n"
                f"import json\n"
                f"import os\n\n"
                f"print(f'Executing: {title}')\n"
                f"result = {{'task': '{title}', 'status': 'completed', 'goal': '{goal[:50]}'}}\n"
                f"print(json.dumps(result, indent=2))\n"
            )
            return params

        return params

    def _make_event_callback(self, stream: ActivityStream) -> Callable:
        """Create an event callback for the scheduler."""
        async def callback(event_type: str, data: dict) -> None:
            level = "error" if "failed" in event_type else (
                "success" if "completed" in event_type else "info"
            )
            await stream.emit(event_type, data, level=level)
        return callback

    async def _persist_results(self, ctx: ExecutionContext, tasks: dict) -> None:
        """Persist tool results to database."""
        for task_id, task in tasks.items():
            if task.result is not None:
                try:
                    processed = str(task.result)[:5000]
                    await self.result_store.save_result(
                        conn=ctx.conn,
                        execution_id=ctx.execution_id,
                        task_id=task_id,
                        tool_id=task.tool_id,
                        status=task.state.value,
                        raw_output=task.result if isinstance(task.result, dict) else {"output": str(task.result)},
                        processed_output=processed,
                        execution_time_ms=task.execution_time_ms,
                    )
                except Exception as e:
                    logger.warning(f"[ExecutionEngine] Failed to persist result for {task_id}: {e}")

    async def _save_report(self, ctx: ExecutionContext, report: ExecutionReport) -> None:
        """Save execution report to database."""
        try:
            await ctx.conn.execute(
                """INSERT INTO task_reports
                   (id, execution_id, goal, report_markdown, report_data, created_at)
                   VALUES ($1,$2,$3,$4,$5, NOW())
                   ON CONFLICT (id) DO NOTHING""",
                str(uuid.uuid4()),
                ctx.execution_id,
                ctx.goal[:500],
                report.report_markdown,
                json.dumps(report.to_dict()),
            )
        except Exception as e:
            logger.warning(f"[ExecutionEngine] Failed to save report: {e}")

    async def _generate_partial_report(self, ctx: ExecutionContext) -> ExecutionReport:
        """Generate a partial report when execution is cancelled."""
        report = self.report_generator.generate(
            execution_id=ctx.execution_id,
            goal=ctx.goal,
            tasks=ctx.tasks,
            events=ctx.stream.get_all_events(),
            partial=True,
        )
        try:
            await self._save_report(ctx, report)
        except Exception:
            pass
        return report
