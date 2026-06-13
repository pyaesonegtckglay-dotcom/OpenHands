"""
Planner Trigger
Determines whether a plan should be generated and at what depth.

Rules:
- CHAT       → No Planning
- QUESTION   → No Planning
- TASK       → Conditional Planning (complexity >= 6)
- PROJECT    → Planning Required
- WORKFLOW   → Planning Required
- COMMAND    → Conditional Planning (complexity >= 7)

Plan Depth:
- Complexity 1-3   → No Plan
- Complexity 4-5   → shallow (3-5 steps)
- Complexity 6-7   → medium (5-10 steps)
- Complexity 8-10  → deep (10-30 steps)
"""

import logging
from enum import Enum
from dataclasses import dataclass
from app.agent.intent_classifier import IntentType
from app.agent.task_classifier import TaskType

logger = logging.getLogger(__name__)


class PlanDepth(str, Enum):
    NONE = "none"
    SHALLOW = "shallow"     # 3-5 steps
    MEDIUM = "medium"       # 5-10 steps
    DEEP = "deep"           # 10-30 steps


@dataclass
class PlannerDecision:
    planning_required: bool
    plan_depth: PlanDepth
    min_steps: int
    max_steps: int
    reason: str


# Rules: (intent, task_type) → planning rule
# "always" = always plan
# "never" = never plan
# "conditional" = depends on complexity
PLANNING_RULES = {
    IntentType.CHAT: "never",
    IntentType.QUESTION: "never",
    IntentType.PROJECT: "always",
    IntentType.WORKFLOW: "always",
    IntentType.TASK: "conditional",
    IntentType.COMMAND: "conditional",
}

TASK_TYPE_OVERRIDES = {
    TaskType.CHAT: "never",
    TaskType.KNOWLEDGE: "never",
    TaskType.PROJECT: "always",
    TaskType.WORKFLOW: "always",
    TaskType.CODING: "conditional",
    TaskType.RESEARCH: "conditional",
    TaskType.ANALYSIS: "conditional",
    TaskType.WRITING: "conditional",
}

# Thresholds for conditional planning
CONDITIONAL_THRESHOLD = 5  # complexity >= 5 triggers planning for conditional types


def _get_plan_depth(complexity: int) -> tuple[PlanDepth, int, int]:
    """Return (depth, min_steps, max_steps) based on complexity."""
    if complexity <= 3:
        return PlanDepth.NONE, 0, 0
    elif complexity <= 5:
        return PlanDepth.SHALLOW, 3, 5
    elif complexity <= 7:
        return PlanDepth.MEDIUM, 5, 10
    else:
        return PlanDepth.DEEP, 10, 30


class PlannerTrigger:
    """
    Decision layer: should a plan be generated?
    """

    def decide(
        self,
        intent: IntentType,
        task_type: TaskType,
        complexity: int,
    ) -> PlannerDecision:
        """Decide whether planning is needed."""
        logger.debug(
            f"Planner trigger: intent={intent.value}, "
            f"task_type={task_type.value}, complexity={complexity}"
        )

        # Task type can override intent rule
        task_rule = TASK_TYPE_OVERRIDES.get(task_type, "conditional")
        intent_rule = PLANNING_RULES.get(intent, "conditional")

        # Task type override takes priority if it's definitive
        if task_rule == "never" or intent_rule == "never":
            return PlannerDecision(
                planning_required=False,
                plan_depth=PlanDepth.NONE,
                min_steps=0,
                max_steps=0,
                reason=(
                    f"No planning for intent='{intent.value}' / "
                    f"task_type='{task_type.value}'"
                ),
            )

        if task_rule == "always" or intent_rule == "always":
            depth, min_steps, max_steps = _get_plan_depth(complexity)
            return PlannerDecision(
                planning_required=True,
                plan_depth=depth,
                min_steps=min_steps,
                max_steps=max_steps,
                reason=(
                    f"Planning required for intent='{intent.value}' / "
                    f"task_type='{task_type.value}'"
                ),
            )

        # Conditional: check complexity threshold
        if complexity >= CONDITIONAL_THRESHOLD:
            depth, min_steps, max_steps = _get_plan_depth(complexity)
            return PlannerDecision(
                planning_required=True,
                plan_depth=depth,
                min_steps=min_steps,
                max_steps=max_steps,
                reason=(
                    f"Conditional planning triggered: complexity={complexity} "
                    f">= threshold={CONDITIONAL_THRESHOLD}"
                ),
            )

        return PlannerDecision(
            planning_required=False,
            plan_depth=PlanDepth.NONE,
            min_steps=0,
            max_steps=0,
            reason=(
                f"No planning needed: complexity={complexity} "
                f"< threshold={CONDITIONAL_THRESHOLD}"
            ),
        )
