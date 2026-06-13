"""
Plan Generator
Generates structured, step-by-step plans using AI providers.
Plans are COGNITIVE only — no execution is generated.
"""

import json
import uuid
import logging
from dataclasses import dataclass, field
from app.agent.provider_router import ProviderRouter, ProviderName
from app.agent.planner_trigger import PlanDepth

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a cognitive planning assistant. Your job is to create structured, 
actionable plans for tasks. You ONLY plan — you do NOT execute.

Generate a JSON plan with the following structure:
{
  "plan_id": "<uuid>",
  "goal": "<clear goal statement>",
  "steps": [
    {
      "id": "<step_id e.g. step_1>",
      "title": "<short title>",
      "description": "<what this step involves>",
      "expected_output": "<what this step produces>",
      "dependencies": [],
      "status": "pending"
    }
  ]
}

Rules:
- Every step MUST have: id, title, description, expected_output, dependencies, status
- status is always "pending" 
- dependencies is a list of step IDs this step depends on (empty array if none)
- steps must be logically ordered
- No execution code, no running anything — planning only
- Return ONLY valid JSON, no markdown, no explanation outside the JSON
"""


@dataclass
class PlanStep:
    id: str
    title: str
    description: str
    expected_output: str
    dependencies: list[str] = field(default_factory=list)
    status: str = "pending"


@dataclass
class PlanObject:
    plan_id: str
    goal: str
    steps: list[PlanStep]
    provider_used: str = ""
    model_used: str = ""
    plan_depth: str = "medium"
    error: str | None = None


def _build_prompt(goal: str, depth: PlanDepth, min_steps: int, max_steps: int) -> str:
    depth_instruction = {
        PlanDepth.SHALLOW: f"Create a concise plan with {min_steps}-{max_steps} steps.",
        PlanDepth.MEDIUM: f"Create a detailed plan with {min_steps}-{max_steps} steps.",
        PlanDepth.DEEP: f"Create a comprehensive plan with {min_steps}-{max_steps} steps covering all aspects.",
    }.get(depth, f"Create a plan with {min_steps}-{max_steps} steps.")

    return f"""Goal: {goal}

{depth_instruction}

Remember:
- This is cognitive planning ONLY. No execution.
- Each step must have a clear expected output.
- Steps must have logical dependencies.
- Return ONLY valid JSON following the exact structure.
"""


def _parse_plan(content: str, goal: str) -> PlanObject | None:
    """Parse AI response into PlanObject."""
    if not content or not content.strip():
        return None

    # Extract JSON from potential markdown fences
    text = content.strip()
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
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse plan JSON: {e}")
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except Exception:
                return None
        else:
            return None

    # Validate required fields
    if "steps" not in data or not isinstance(data.get("steps"), list):
        logger.warning("Plan missing 'steps' field")
        return None

    plan_id = data.get("plan_id", str(uuid.uuid4()))
    plan_goal = data.get("goal", goal)

    steps = []
    for i, step_data in enumerate(data["steps"]):
        if not isinstance(step_data, dict):
            continue
        step = PlanStep(
            id=step_data.get("id", f"step_{i + 1}"),
            title=step_data.get("title", f"Step {i + 1}"),
            description=step_data.get("description", ""),
            expected_output=step_data.get("expected_output", ""),
            dependencies=step_data.get("dependencies", []),
            status=step_data.get("status", "pending"),
        )
        steps.append(step)

    if not steps:
        return None

    return PlanObject(
        plan_id=plan_id,
        goal=plan_goal,
        steps=steps,
    )


def _generate_fallback_plan(goal: str, depth: PlanDepth, min_steps: int, max_steps: int) -> PlanObject:
    """Generate a template plan when AI providers are unavailable."""
    plan_id = str(uuid.uuid4())
    num_steps = min(max(min_steps, 3), min(max_steps, 7))  # Between 3-7 steps

    steps = [
        PlanStep(
            id="step_1",
            title="Requirements Analysis",
            description=f"Analyze and define the requirements for: {goal}",
            expected_output="Clear list of requirements and success criteria",
            dependencies=[],
            status="pending",
        ),
        PlanStep(
            id="step_2",
            title="Research and Planning",
            description="Research best approaches, tools, and technologies",
            expected_output="Technical approach document with selected tools",
            dependencies=["step_1"],
            status="pending",
        ),
        PlanStep(
            id="step_3",
            title="Design and Architecture",
            description="Design the solution architecture and component structure",
            expected_output="Architecture diagram and component specifications",
            dependencies=["step_2"],
            status="pending",
        ),
    ]

    if num_steps >= 5:
        steps += [
            PlanStep(
                id="step_4",
                title="Implementation Phase 1",
                description="Implement core components and foundation",
                expected_output="Working core implementation",
                dependencies=["step_3"],
                status="pending",
            ),
            PlanStep(
                id="step_5",
                title="Implementation Phase 2",
                description="Implement remaining features and integrations",
                expected_output="Complete feature implementation",
                dependencies=["step_4"],
                status="pending",
            ),
        ]

    if num_steps >= 7:
        steps += [
            PlanStep(
                id="step_6",
                title="Testing and Validation",
                description="Test all components and validate against requirements",
                expected_output="Test results and validation report",
                dependencies=["step_5"],
                status="pending",
            ),
            PlanStep(
                id="step_7",
                title="Documentation and Delivery",
                description="Document the solution and prepare for delivery",
                expected_output="Complete documentation and deliverable package",
                dependencies=["step_6"],
                status="pending",
            ),
        ]

    return PlanObject(
        plan_id=plan_id,
        goal=goal,
        steps=steps[:num_steps],
        provider_used="fallback_template",
        model_used="none",
        plan_depth=depth.value,
    )


class PlanGenerator:
    """
    Generates cognitive plans using AI providers.
    Falls back to template plans if all providers fail.
    """

    def __init__(self):
        self.router = ProviderRouter()

    async def generate(
        self,
        goal: str,
        depth: PlanDepth = PlanDepth.MEDIUM,
        min_steps: int = 5,
        max_steps: int = 10,
    ) -> PlanObject:
        """Generate a structured plan for the given goal."""
        logger.info(f"Generating plan for goal: {goal[:80]}... depth={depth.value}")

        if depth == PlanDepth.NONE:
            return PlanObject(
                plan_id=str(uuid.uuid4()),
                goal=goal,
                steps=[],
                plan_depth=depth.value,
                error="No planning required for this task",
            )

        prompt = _build_prompt(goal, depth, min_steps, max_steps)

        provider_result = await self.router.complete(prompt, SYSTEM_PROMPT)

        if provider_result.provider == ProviderName.NONE or not provider_result.content:
            logger.warning("All providers failed, using fallback template plan")
            fallback = _generate_fallback_plan(goal, depth, min_steps, max_steps)
            fallback.error = "AI providers unavailable, using template plan"
            return fallback

        plan = _parse_plan(provider_result.content, goal)
        if not plan:
            logger.warning("Failed to parse AI plan, using fallback template")
            fallback = _generate_fallback_plan(goal, depth, min_steps, max_steps)
            fallback.provider_used = provider_result.provider.value
            fallback.error = "Plan parsing failed, using template plan"
            return fallback

        plan.provider_used = provider_result.provider.value
        plan.model_used = provider_result.model
        plan.plan_depth = depth.value

        logger.info(
            f"Plan generated: {len(plan.steps)} steps, "
            f"provider={provider_result.provider.value}"
        )
        return plan
