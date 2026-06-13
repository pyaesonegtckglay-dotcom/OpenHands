"""
Task Decomposer — Phase 2
Converts plan steps into atomic, independently executable tasks.
Follows ATOMIC TASK RULE: every task must be independently executable.

Rules:
- Bad: "Research Tesla"
- Good: "Find Tesla official website", "Extract company information", ...
"""

import uuid
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.agent.provider_router import ProviderRouter, ProviderName

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    BLOCKED = "BLOCKED"
    WAITING = "WAITING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class TaskComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class AtomicTask:
    """A single atomic task — the smallest independently executable unit."""
    id: str
    title: str
    description: str
    expected_output: str
    estimated_complexity: TaskComplexity
    estimated_duration: str          # e.g. "5-10 minutes"
    parent_task: Optional[str]       # parent task id
    child_tasks: list[str]           # child task ids
    dependencies: list[str]          # ids of tasks this task depends on
    status: TaskStatus = TaskStatus.PLANNED
    order: int = 0
    parallelizable: bool = True
    is_blocking: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "expected_output": self.expected_output,
            "estimated_complexity": self.estimated_complexity.value,
            "estimated_duration": self.estimated_duration,
            "parent_task": self.parent_task,
            "child_tasks": self.child_tasks,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "order": self.order,
            "parallelizable": self.parallelizable,
            "is_blocking": self.is_blocking,
        }


DECOMPOSER_SYSTEM_PROMPT = """You are a task decomposition engine. Your job is to break down a high-level goal and its plan steps into atomic, independently executable tasks.

ATOMIC TASK RULE:
- Every task must be independently executable
- Bad: "Research Tesla" 
- Good: "Find Tesla official website", "Extract company information from Tesla website", "List Tesla products"

OUTPUT FORMAT — Return ONLY valid JSON, no markdown, no explanation:
{
  "tasks": [
    {
      "id": "task_<n>",
      "title": "<short, specific action title>",
      "description": "<detailed description of what this task does>",
      "expected_output": "<concrete deliverable this task produces>",
      "estimated_complexity": "<low|medium|high>",
      "estimated_duration": "<e.g. 2-5 minutes>",
      "parent_task": "<parent_task_id or null>",
      "child_tasks": [],
      "dependencies": ["<task_id>", ...],
      "order": <integer order>,
      "parallelizable": <true|false>,
      "is_blocking": <true|false>
    }
  ]
}

Rules:
- parallelizable=true if task can run alongside sibling tasks
- is_blocking=true if dependent tasks cannot start until this completes
- All tasks start with status "PLANNED"
- dependencies[] lists task ids that must complete BEFORE this task starts
- Return ONLY valid JSON
"""


def _build_decompose_prompt(goal: str, plan_steps: list[dict]) -> str:
    steps_text = "\n".join(
        f"  Step {i+1}: {s.get('title', '')} — {s.get('description', '')}"
        for i, s in enumerate(plan_steps)
    )
    return f"""Goal: {goal}

Plan Steps:
{steps_text}

Decompose each plan step into 2-4 atomic tasks. Create a complete task hierarchy.
Identify which tasks can run in parallel and which are blocking.
Return the complete task list as JSON."""


def _parse_tasks(content: str, goal: str) -> list[AtomicTask]:
    """Parse AI response into list of AtomicTask."""
    text = content.strip()
    # Strip markdown
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end].strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except Exception:
                return []
        else:
            return []

    raw_tasks = data.get("tasks", [])
    if not isinstance(raw_tasks, list):
        return []

    tasks = []
    for i, t in enumerate(raw_tasks):
        if not isinstance(t, dict):
            continue
        try:
            complexity_raw = t.get("estimated_complexity", "medium").lower()
            complexity = TaskComplexity(complexity_raw) if complexity_raw in [e.value for e in TaskComplexity] else TaskComplexity.MEDIUM
            task = AtomicTask(
                id=t.get("id", f"task_{i+1}"),
                title=t.get("title", f"Task {i+1}"),
                description=t.get("description", ""),
                expected_output=t.get("expected_output", ""),
                estimated_complexity=complexity,
                estimated_duration=t.get("estimated_duration", "5-10 minutes"),
                parent_task=t.get("parent_task"),
                child_tasks=t.get("child_tasks", []),
                dependencies=t.get("dependencies", []),
                status=TaskStatus.PLANNED,
                order=t.get("order", i),
                parallelizable=bool(t.get("parallelizable", True)),
                is_blocking=bool(t.get("is_blocking", False)),
            )
            tasks.append(task)
        except Exception as e:
            logger.warning(f"Failed to parse task {i}: {e}")
            continue

    return tasks


def _generate_fallback_tasks(goal: str, plan_steps: list[dict]) -> list[AtomicTask]:
    """Generate atomic tasks from plan steps when AI is unavailable."""
    tasks = []
    task_counter = 1

    for step_idx, step in enumerate(plan_steps):
        step_title = step.get("title", f"Step {step_idx+1}")
        step_desc = step.get("description", "")
        step_id = step.get("id", f"step_{step_idx+1}")

        # Create 2-3 atomic subtasks per step
        sub_tasks = [
            AtomicTask(
                id=f"task_{task_counter}",
                title=f"Prepare: {step_title}",
                description=f"Gather required information and resources for: {step_desc}",
                expected_output=f"Resources and prerequisites ready for {step_title}",
                estimated_complexity=TaskComplexity.LOW,
                estimated_duration="5-10 minutes",
                parent_task=step_id,
                child_tasks=[],
                dependencies=[] if step_idx == 0 else [f"task_{task_counter - 2}"],
                status=TaskStatus.PLANNED,
                order=task_counter - 1,
                parallelizable=True,
                is_blocking=False,
            ),
            AtomicTask(
                id=f"task_{task_counter+1}",
                title=f"Execute: {step_title}",
                description=f"Perform the core work: {step_desc}",
                expected_output=step.get("expected_output", f"Completed output for {step_title}"),
                estimated_complexity=TaskComplexity.MEDIUM,
                estimated_duration="15-30 minutes",
                parent_task=step_id,
                child_tasks=[],
                dependencies=[f"task_{task_counter}"],
                status=TaskStatus.PLANNED,
                order=task_counter,
                parallelizable=False,
                is_blocking=True,
            ),
        ]
        tasks.extend(sub_tasks)
        task_counter += 2

    # Fix child_tasks references
    task_map = {t.id: t for t in tasks}
    for task in tasks:
        for dep_id in task.dependencies:
            if dep_id in task_map:
                parent = task_map[dep_id]
                if task.id not in parent.child_tasks:
                    parent.child_tasks.append(task.id)

    return tasks


class TaskDecomposer:
    """
    Decomposes plan steps into atomic tasks with hierarchy, dependencies,
    parallel markers, and blocking markers.
    Phase 2 — planning only, no execution.
    """

    def __init__(self):
        self.router = ProviderRouter()

    async def decompose(self, goal: str, plan_steps: list[dict]) -> list[AtomicTask]:
        """
        Break down plan steps into atomic tasks.

        Args:
            goal: The overall goal
            plan_steps: List of plan step dicts from Phase 1

        Returns:
            List of AtomicTask with full hierarchy and dependency info
        """
        logger.info(f"Decomposing {len(plan_steps)} steps for goal: {goal[:60]}...")

        if not plan_steps:
            logger.warning("No plan steps provided — generating default tasks")
            return self._generate_goal_tasks(goal)

        prompt = _build_decompose_prompt(goal, plan_steps)
        provider_result = await self.router.complete(prompt, DECOMPOSER_SYSTEM_PROMPT)

        if provider_result.provider == ProviderName.NONE or not provider_result.content:
            logger.warning("AI unavailable, using fallback task decomposition")
            return _generate_fallback_tasks(goal, plan_steps)

        tasks = _parse_tasks(provider_result.content, goal)

        if not tasks:
            logger.warning("Failed to parse AI tasks, using fallback")
            return _generate_fallback_tasks(goal, plan_steps)

        logger.info(f"Decomposed into {len(tasks)} atomic tasks via {provider_result.provider.value}")
        return tasks

    def _generate_goal_tasks(self, goal: str) -> list[AtomicTask]:
        """Generate a minimal set of tasks from just the goal."""
        return [
            AtomicTask(
                id="task_1",
                title="Analyze Goal",
                description=f"Analyze and understand the requirements for: {goal}",
                expected_output="Clear understanding of goal requirements",
                estimated_complexity=TaskComplexity.LOW,
                estimated_duration="5 minutes",
                parent_task=None,
                child_tasks=["task_2"],
                dependencies=[],
                order=0,
                parallelizable=False,
                is_blocking=True,
            ),
            AtomicTask(
                id="task_2",
                title="Research and Plan",
                description=f"Research best approaches for: {goal}",
                expected_output="Approach document with selected methodology",
                estimated_complexity=TaskComplexity.MEDIUM,
                estimated_duration="10-20 minutes",
                parent_task=None,
                child_tasks=["task_3"],
                dependencies=["task_1"],
                order=1,
                parallelizable=False,
                is_blocking=True,
            ),
            AtomicTask(
                id="task_3",
                title="Execute Core Work",
                description=f"Perform the main work for: {goal}",
                expected_output="Primary deliverable",
                estimated_complexity=TaskComplexity.HIGH,
                estimated_duration="30-60 minutes",
                parent_task=None,
                child_tasks=["task_4"],
                dependencies=["task_2"],
                order=2,
                parallelizable=False,
                is_blocking=True,
            ),
            AtomicTask(
                id="task_4",
                title="Review and Finalize",
                description="Review outputs and prepare final deliverable",
                expected_output="Final reviewed deliverable",
                estimated_complexity=TaskComplexity.LOW,
                estimated_duration="10 minutes",
                parent_task=None,
                child_tasks=[],
                dependencies=["task_3"],
                order=3,
                parallelizable=False,
                is_blocking=False,
            ),
        ]
