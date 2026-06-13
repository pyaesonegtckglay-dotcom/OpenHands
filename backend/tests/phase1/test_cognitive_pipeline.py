"""
Tests for CognitivePipeline — Phase 1 Integration Test
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.agent.cognitive_pipeline import CognitivePipeline, CognitiveAnalysisResult
from app.agent.provider_router import ProviderResult, ProviderName


@pytest.fixture
def pipeline():
    return CognitivePipeline()


class TestAnalyzeEndpoint:
    @pytest.mark.asyncio
    async def test_analyze_chat(self, pipeline):
        result = await pipeline.analyze("Hello!")
        assert result.intent == "CHAT"
        assert result.planning_required is False

    @pytest.mark.asyncio
    async def test_analyze_question(self, pipeline):
        result = await pipeline.analyze("What is Python?")
        assert result.intent == "QUESTION"
        assert result.planning_required is False

    @pytest.mark.asyncio
    async def test_analyze_project(self, pipeline):
        result = await pipeline.analyze("Build a full-stack SaaS application")
        assert result.intent == "PROJECT"
        assert result.planning_required is True

    @pytest.mark.asyncio
    async def test_analyze_returns_all_fields(self, pipeline):
        result = await pipeline.analyze("Build a portfolio website")
        assert isinstance(result, CognitiveAnalysisResult)
        assert result.intent
        assert result.complexity >= 1
        assert result.complexity <= 10
        assert result.task_type
        assert result.plan_depth
        assert result.goal

    @pytest.mark.asyncio
    async def test_chat_complexity_is_low(self, pipeline):
        result = await pipeline.analyze("Hi there!")
        assert result.complexity <= 3

    @pytest.mark.asyncio
    async def test_project_complexity_is_high(self, pipeline):
        result = await pipeline.analyze(
            "Build a complete e-commerce platform with authentication, "
            "payment processing, and admin dashboard"
        )
        assert result.complexity >= 6

    @pytest.mark.asyncio
    async def test_planner_no_run_for_chat(self, pipeline):
        """Planner must NOT run for chat messages."""
        result = await pipeline.analyze("Good morning!")
        assert result.planning_required is False
        assert result.plan_depth == "none"

    @pytest.mark.asyncio
    async def test_planner_runs_for_project(self, pipeline):
        """Planner MUST run for project messages."""
        result = await pipeline.analyze(
            "Build a complete web application with authentication and database"
        )
        assert result.planning_required is True
        assert result.plan_depth in ("shallow", "medium", "deep")


class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_chat_no_plan(self, pipeline):
        """Full pipeline for chat should not generate a plan."""
        result = await pipeline.run_full_pipeline("Hello there!")
        assert result.analysis.intent == "CHAT"
        assert result.plan is None

    @pytest.mark.asyncio
    async def test_full_pipeline_project_generates_plan(self, pipeline):
        """Full pipeline for project should generate a plan."""
        mock_result = ProviderResult(
            provider=ProviderName.NONE,
            model="none",
            content="",
        )
        with patch(
            "app.agent.provider_router.router._call_gemini",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.agent.provider_router.router._call_github_models",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.agent.provider_router.router._call_sambanova",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await pipeline.run_full_pipeline(
                "Build a full-stack SaaS application"
            )
            assert result.analysis.planning_required is True
            # Even with provider failures, fallback plan should be generated
            assert result.plan is not None
            assert len(result.plan["steps"]) >= 3
