"""
Tests for ComplexityAnalyzer — Phase 1
"""

import pytest
from app.agent.complexity_analyzer import ComplexityAnalyzer, ComplexityResult
from app.agent.intent_classifier import IntentType


@pytest.fixture
def analyzer():
    return ComplexityAnalyzer()


class TestComplexityScores:
    def test_chat_is_low(self, analyzer):
        result = analyzer.analyze("Hello", IntentType.CHAT)
        assert result.complexity <= 3

    def test_simple_question_is_low(self, analyzer):
        result = analyzer.analyze("What is Python?", IntentType.QUESTION)
        assert result.complexity <= 5

    def test_task_is_medium(self, analyzer):
        result = analyzer.analyze("Find 10 VPS providers", IntentType.TASK)
        assert 4 <= result.complexity <= 7

    def test_project_is_high(self, analyzer):
        result = analyzer.analyze(
            "Build a full-stack SaaS application with authentication and database",
            IntentType.PROJECT
        )
        assert result.complexity >= 7

    def test_complex_system_is_enterprise(self, analyzer):
        result = analyzer.analyze(
            "Build a complete e-commerce platform with microservices, "
            "authentication, payment processing, real-time notifications, "
            "admin dashboard, mobile app, CI/CD pipeline, and Kubernetes deployment",
            IntentType.PROJECT
        )
        assert result.complexity >= 9

    def test_score_range(self, analyzer):
        result = analyzer.analyze("Build something", IntentType.TASK)
        assert 1 <= result.complexity <= 10

    def test_has_complexity_level(self, analyzer):
        result = analyzer.analyze("Hello", IntentType.CHAT)
        assert result.complexity_level in ("trivial", "simple", "moderate", "complex", "enterprise")

    def test_has_reasoning(self, analyzer):
        result = analyzer.analyze("Build a website", IntentType.PROJECT)
        assert len(result.reasoning) > 0

    def test_trivial_level(self, analyzer):
        result = analyzer.analyze("Hi", IntentType.CHAT)
        assert result.complexity_level == "trivial"

    def test_enterprise_level(self, analyzer):
        result = analyzer.analyze(
            "Build a distributed microservices e-commerce platform with real-time "
            "streaming, machine learning recommendations, full authentication, "
            "payment integration, CI/CD, Kubernetes, and mobile apps",
            IntentType.PROJECT
        )
        assert result.complexity_level in ("complex", "enterprise")

    def test_workflow_is_complex(self, analyzer):
        result = analyzer.analyze(
            "Research competitors and analyze the market then generate a PDF report "
            "with visualizations and send it via email automatically",
            IntentType.WORKFLOW
        )
        assert result.complexity >= 7
