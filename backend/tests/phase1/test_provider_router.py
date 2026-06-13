"""
Tests for ProviderRouter — Phase 1
Tests verify routing structure and response handling (mocked API calls).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agent.provider_router import ProviderRouter, ProviderName, ProviderResult


@pytest.fixture
def router():
    return ProviderRouter()


class TestProviderRouterStructure:
    def test_router_instantiates(self, router):
        assert router is not None

    def test_provider_names(self):
        assert ProviderName.GEMINI == "gemini"
        assert ProviderName.GITHUB_MODELS == "github_models"
        assert ProviderName.SAMBANOVA == "sambanova"
        assert ProviderName.NONE == "none"

    def test_provider_result_structure(self):
        result = ProviderResult(
            provider=ProviderName.GEMINI,
            model="gemini-1.5-flash",
            content="Test content",
            tokens_used=100,
            attempts=1,
        )
        assert result.provider == ProviderName.GEMINI
        assert result.content == "Test content"


class TestProviderRouting:
    @pytest.mark.asyncio
    async def test_gemini_success(self, router):
        """Test Gemini provider returns successfully."""
        with patch(
            "app.agent.provider_router.router._call_gemini",
            new_callable=AsyncMock,
            return_value="Gemini response",
        ):
            result = await router.complete("Test prompt")
            assert result.provider == ProviderName.GEMINI
            assert result.content == "Gemini response"

    @pytest.mark.asyncio
    async def test_fallback_to_github(self, router):
        """Test fallback to GitHub Models when Gemini fails."""
        with patch(
            "app.agent.provider_router.router._call_gemini",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.agent.provider_router.router._call_github_models",
            new_callable=AsyncMock,
            return_value="GitHub response",
        ):
            result = await router.complete("Test prompt")
            assert result.provider == ProviderName.GITHUB_MODELS
            assert result.content == "GitHub response"

    @pytest.mark.asyncio
    async def test_fallback_to_sambanova(self, router):
        """Test fallback to SambaNova when both Gemini and GitHub fail."""
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
            return_value="SambaNova response",
        ):
            result = await router.complete("Test prompt")
            assert result.provider == ProviderName.SAMBANOVA
            assert result.content == "SambaNova response"

    @pytest.mark.asyncio
    async def test_all_providers_fail(self, router):
        """Test behavior when all providers fail."""
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
            result = await router.complete("Test prompt")
            assert result.provider == ProviderName.NONE
            assert result.content == ""

    @pytest.mark.asyncio
    async def test_attempts_tracked(self, router):
        """Test that attempts are tracked correctly."""
        with patch(
            "app.agent.provider_router.router._call_gemini",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.agent.provider_router.router._call_github_models",
            new_callable=AsyncMock,
            return_value="Response",
        ):
            result = await router.complete("Test prompt")
            assert result.attempts >= 2
