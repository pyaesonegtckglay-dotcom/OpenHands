"""
Tests for PlanValidator — Phase 1
"""

import pytest
from app.agent.plan_validator import PlanValidator
from app.agent.planner import PlanObject, PlanStep


@pytest.fixture
def validator():
    return PlanValidator()


def make_plan(steps=None, goal="Test goal", plan_id="test-plan-id"):
    if steps is None:
        steps = [
            PlanStep(id="step_1", title="Step 1", description="Do step 1",
                     expected_output="Output 1", dependencies=[], status="pending"),
            PlanStep(id="step_2", title="Step 2", description="Do step 2",
                     expected_output="Output 2", dependencies=["step_1"], status="pending"),
        ]
    return PlanObject(plan_id=plan_id, goal=goal, steps=steps)


class TestValidPlan:
    def test_valid_plan_passes(self, validator):
        plan = make_plan()
        result = validator.validate(plan)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_plan_step_count(self, validator):
        plan = make_plan()
        result = validator.validate(plan)
        assert result.step_count == 2


class TestInvalidPlans:
    def test_empty_steps(self, validator):
        plan = make_plan(steps=[])
        result = validator.validate(plan)
        assert result.is_valid is False

    def test_too_few_steps(self, validator):
        plan = make_plan(steps=[
            PlanStep(id="step_1", title="Only step", description="Only one",
                     expected_output="Output", dependencies=[], status="pending")
        ])
        result = validator.validate(plan)
        assert result.is_valid is False
        assert any("minimum" in e.lower() for e in result.errors)

    def test_duplicate_step_ids(self, validator):
        plan = make_plan(steps=[
            PlanStep(id="step_1", title="Step 1", description="Desc",
                     expected_output="Output", dependencies=[], status="pending"),
            PlanStep(id="step_1", title="Step 2", description="Desc",
                     expected_output="Output", dependencies=[], status="pending"),
        ])
        result = validator.validate(plan)
        assert result.is_valid is False
        assert any("duplicate" in e.lower() for e in result.errors)

    def test_invalid_dependency(self, validator):
        plan = make_plan(steps=[
            PlanStep(id="step_1", title="Step 1", description="Desc",
                     expected_output="Output", dependencies=[], status="pending"),
            PlanStep(id="step_2", title="Step 2", description="Desc",
                     expected_output="Output", dependencies=["nonexistent_step"], status="pending"),
        ])
        result = validator.validate(plan)
        assert result.is_valid is False
        assert any("nonexistent_step" in e for e in result.errors)

    def test_missing_description(self, validator):
        plan = make_plan(steps=[
            PlanStep(id="step_1", title="Step 1", description="",
                     expected_output="Output", dependencies=[], status="pending"),
            PlanStep(id="step_2", title="Step 2", description="Desc",
                     expected_output="Output", dependencies=[], status="pending"),
        ])
        result = validator.validate(plan)
        assert result.is_valid is False
        assert any("description" in e.lower() for e in result.errors)

    def test_missing_expected_output(self, validator):
        plan = make_plan(steps=[
            PlanStep(id="step_1", title="Step 1", description="Desc",
                     expected_output="", dependencies=[], status="pending"),
            PlanStep(id="step_2", title="Step 2", description="Desc",
                     expected_output="Output", dependencies=[], status="pending"),
        ])
        result = validator.validate(plan)
        assert result.is_valid is False
        assert any("expected_output" in e.lower() for e in result.errors)

    def test_none_plan(self, validator):
        result = validator.validate(None)
        assert result.is_valid is False

    def test_empty_goal(self, validator):
        plan = make_plan(goal="")
        result = validator.validate(plan)
        assert result.is_valid is False

    def test_self_dependency(self, validator):
        plan = make_plan(steps=[
            PlanStep(id="step_1", title="Step 1", description="Desc",
                     expected_output="Output", dependencies=["step_1"], status="pending"),
            PlanStep(id="step_2", title="Step 2", description="Desc",
                     expected_output="Output", dependencies=[], status="pending"),
        ])
        result = validator.validate(plan)
        assert result.is_valid is False


class TestMaxSteps:
    def test_too_many_steps(self, validator):
        steps = [
            PlanStep(
                id=f"step_{i}", title=f"Step {i}", description=f"Desc {i}",
                expected_output=f"Output {i}", dependencies=[], status="pending"
            )
            for i in range(1, 55)  # 54 steps, over max 50
        ]
        plan = make_plan(steps=steps)
        result = validator.validate(plan)
        assert result.is_valid is False
        assert any("maximum" in e.lower() for e in result.errors)
