"""
Tests for PlanGenerator — Phase 1
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.agent.planner import PlanGenerator, PlanObject, PlanStep
from app.agent.provider_router import ProviderResult, ProviderName
from app.agent.planner_trigger import PlanDepth


@pytest.fixture
def generator():
    return PlanGenerator()


SAMPLE_PLAN_JSON = """{
    "plan_id": "test-plan-123",
    "goal": "Build a portfolio website",
    "steps": [
        {
            "id": "step_1",
            "title": "Requirements Gathering",
            "description": "Define website requirements and design",
            "expected_output": "Requirements document",
            "dependencies": [],
            "status": "pending"
        },
        {
            "id": "step_2",
            "title": "Frontend Development",
            "description": "Build the React frontend",
            "expected_output": "Working frontend",
            "dependencies": ["step_1"],
            "status": "pending"
        },
        {
            "id": "step_3",
            "title": "Backend Development",
            "description": "Build the FastAPI backend",
            "expected_output": "Working API",
            "dependencies": ["step_1"],
            "status": "pending"
        }
    ]
}"""


class TestPlanGeneratorStructure:
    def test_generator_instantiates(self, generator):
        assert generator is not None

    def test_has_router(self, generator):
        assert generator.router is not None


class TestPlanGeneration:
    @pytest.mark.asyncio
    async def test_generates_plan_from_ai(self, generator):
        mock_result = ProviderResult(
            provider=ProviderName.GEMINI,
            model="gemini-1.5-flash",
            content=SAMPLE_PLAN_JSON,
        )
        with patch.object(generator.router, "complete", new_callable=AsyncMock, return_value=mock_result):
            plan = await generator.generate(
                goal="Build a portfolio website",
                depth=PlanDepth.MEDIUM,
                min_steps=3,
                max_steps=10,
            )
            assert isinstance(plan, PlanObject)
            assert len(plan.steps) == 3
            assert plan.goal == "Build a portfolio website"
            assert plan.provider_used == "gemini"

    @pytest.mark.asyncio
    async def test_fallback_template_when_providers_fail(self, generator):
        mock_result = ProviderResult(
            provider=ProviderName.NONE,
            model="none",
            content="",
        )
        with patch.object(generator.router, "complete", new_callable=AsyncMock, return_value=mock_result):
            plan = await generator.generate(
                goal="Build something",
                depth=PlanDepth.MEDIUM,
                min_steps=3,
                max_steps=10,
            )
            assert isinstance(plan, PlanObject)
            assert len(plan.steps) >= 3  # fallback generates at least 3 steps

    @pytest.mark.asyncio
    async def test_no_plan_for_none_depth(self, generator):
        plan = await generator.generate(
            goal="Hello",
            depth=PlanDepth.NONE,
            min_steps=0,
            max_steps=0,
        )
        assert isinstance(plan, PlanObject)
        assert len(plan.steps) == 0

    @pytest.mark.asyncio
    async def test_plan_steps_have_required_fields(self, generator):
        mock_result = ProviderResult(
            provider=ProviderName.GEMINI,
            model="gemini-1.5-flash",
            content=SAMPLE_PLAN_JSON,
        )
        with patch.object(generator.router, "complete", new_callable=AsyncMock, return_value=mock_result):
            plan = await generator.generate(
                goal="Build a portfolio website",
                depth=PlanDepth.MEDIUM,
                min_steps=3,
                max_steps=10,
            )
            for step in plan.steps:
                assert step.id
                assert step.title
                assert step.description
                assert step.expected_output
                assert isinstance(step.dependencies, list)
                assert step.status == "pending"

    @pytest.mark.asyncio
    async def test_handles_malformed_json(self, generator):
        mock_result = ProviderResult(
            provider=ProviderName.GEMINI,
            model="gemini-1.5-flash",
            content="This is not JSON at all",
        )
        with patch.object(generator.router, "complete", new_callable=AsyncMock, return_value=mock_result):
            plan = await generator.generate(
                goal="Build something",
                depth=PlanDepth.MEDIUM,
                min_steps=3,
                max_steps=10,
            )
            assert isinstance(plan, PlanObject)
            # Should fall back to template plan
            assert len(plan.steps) >= 3
