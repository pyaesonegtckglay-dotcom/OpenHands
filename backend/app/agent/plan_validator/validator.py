"""
Plan Validator
Validates plan quality and structure.

Rules:
- No empty plans
- Minimum 2 steps
- Maximum 50 steps
- No duplicate step IDs
- Valid dependencies (all referenced step IDs must exist)
- Expected output required for each step
- Description required for each step
"""

import logging
from dataclasses import dataclass, field
from app.agent.planner import PlanObject

logger = logging.getLogger(__name__)

MIN_STEPS = 2
MAX_STEPS = 50


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    step_count: int = 0


class PlanValidator:
    """
    Validates generated plans against quality rules.
    """

    def validate(self, plan: PlanObject) -> ValidationResult:
        """Validate a plan and return a ValidationResult."""
        errors = []
        warnings = []

        if not plan:
            return ValidationResult(
                is_valid=False,
                errors=["Plan is None"],
            )

        # Empty plan
        if not plan.steps:
            if plan.error:
                # Non-planning decision - not an error
                return ValidationResult(
                    is_valid=True,
                    warnings=["Empty plan (no planning required)"],
                    step_count=0,
                )
            errors.append("Plan has no steps")
            return ValidationResult(is_valid=False, errors=errors)

        step_count = len(plan.steps)

        # Min steps check
        if step_count < MIN_STEPS:
            errors.append(
                f"Plan has {step_count} step(s), minimum is {MIN_STEPS}"
            )

        # Max steps check
        if step_count > MAX_STEPS:
            errors.append(
                f"Plan has {step_count} steps, maximum is {MAX_STEPS}"
            )

        # Collect all step IDs
        step_ids = set()
        duplicate_ids = set()
        for step in plan.steps:
            if step.id in step_ids:
                duplicate_ids.add(step.id)
            step_ids.add(step.id)

        if duplicate_ids:
            errors.append(f"Duplicate step IDs: {', '.join(duplicate_ids)}")

        # Validate each step
        for i, step in enumerate(plan.steps):
            step_label = f"Step {i + 1} ('{step.id}')"

            # Title required
            if not step.title or not step.title.strip():
                errors.append(f"{step_label}: missing title")

            # Description required
            if not step.description or not step.description.strip():
                errors.append(f"{step_label}: missing description")

            # Expected output required
            if not step.expected_output or not step.expected_output.strip():
                errors.append(f"{step_label}: missing expected_output")

            # Validate dependencies
            for dep in step.dependencies:
                if dep not in step_ids:
                    errors.append(
                        f"{step_label}: dependency '{dep}' does not exist"
                    )
                if dep == step.id:
                    errors.append(
                        f"{step_label}: step cannot depend on itself"
                    )

            # Warnings for quality
            if step.title and len(step.title) > 100:
                warnings.append(f"{step_label}: title is very long ({len(step.title)} chars)")
            if step.description and len(step.description) < 10:
                warnings.append(f"{step_label}: description is very short")

        # Check for circular dependencies (simple detection)
        dep_graph = {s.id: set(s.dependencies) for s in plan.steps}
        for step_id in step_ids:
            visited = set()
            stack = [step_id]
            while stack:
                current = stack.pop()
                if current in visited:
                    if current == step_id and len(visited) > 0:
                        warnings.append(
                            f"Possible circular dependency detected involving step '{step_id}'"
                        )
                        break
                    continue
                visited.add(current)
                stack.extend(dep_graph.get(current, []))

        # Goal validation
        if not plan.goal or not plan.goal.strip():
            errors.append("Plan missing goal statement")

        is_valid = len(errors) == 0
        logger.debug(
            f"Plan validation: valid={is_valid}, "
            f"errors={len(errors)}, warnings={len(warnings)}"
        )

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            step_count=step_count,
        )
